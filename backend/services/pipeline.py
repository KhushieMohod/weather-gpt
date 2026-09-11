from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy.orm import Session

from ..connectors.base import BaseConnector
from ..models import RiskAlert, WeatherObservation
from ..risk_engine.engine import evaluate_observation
from .credibility import fusion_engine
from .metrics import (
    ALERTS_TOTAL,
    CONNECTOR_FETCH_TOTAL,
    CONNECTOR_LATENCY_SECONDS,
    INGESTION_BATCH_TOTAL,
    OBSERVATIONS_TOTAL,
    PIPELINE_DURATION_SECONDS,
)
from .validation import add_credibility_log, validate_observation

logger = logging.getLogger(__name__)


@dataclass
class IngestionReport:
    """Summary report of an ingestion batch execution."""
    source: str
    total_received: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    alerts_generated: int = 0
    errors: list[str] = field(default_factory=list)
    alert_summaries: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestPipeline:
    """Production Weather Data Ingestion Pipeline.
    
    Orchestrates:
    1. Validation & sanitization of raw parameter feeds
    2. Multi-source Bayesian credibility scoring
    3. Duplicate detection and historical logging
    4. Database persistence
    5. Real-time hazard risk evaluation
    6. System metrics collection
    """

    def __init__(self, broadcast_fn: Any | None = None) -> None:
        self.broadcast_fn = broadcast_fn

    def process_record(
        self,
        record: dict[str, Any],
        db: Session,
    ) -> tuple[WeatherObservation | None, list[RiskAlert], list[str]]:
        """Process a single observation payload end-to-end within transaction."""
        source = str(record.get("source", "unknown"))
        result = validate_observation(record, db)
        add_credibility_log(db, record, result)

        if result.status != "valid" or not result.normalized:
            OBSERVATIONS_TOTAL.labels(source=source, status="rejected").inc()
            return None, [], result.errors

        # Persist valid observation
        observation = WeatherObservation(**result.normalized)
        db.add(observation)
        db.flush()  # assign ID

        OBSERVATIONS_TOTAL.labels(source=source, status="valid").inc()

        # Risk Engine Evaluation
        alerts = evaluate_observation(db, observation)
        for alert in alerts:
            ALERTS_TOTAL.labels(
                hazard_type=alert.hazard_type,
                severity=alert.severity,
            ).inc()

        return observation, alerts, []

    def process_batch(
        self,
        records: Sequence[dict[str, Any]],
        db: Session,
        source_name: str = "batch",
    ) -> IngestionReport:
        """Process a batch of records transactionally with partial success resilience."""
        start_time = time.time()
        report = IngestionReport(source=source_name, total_received=len(records))

        created_alerts: list[RiskAlert] = []

        for record in records:
            try:
                obs, alerts, errors = self.process_record(record, db)
                if obs:
                    report.valid_count += 1
                    if alerts:
                        report.alerts_generated += len(alerts)
                        created_alerts.extend(alerts)
                else:
                    report.rejected_count += 1
                    report.errors.extend(errors)
            except Exception as exc:
                logger.error("Error processing record: %s", exc)
                report.rejected_count += 1
                report.errors.append(str(exc))

        try:
            db.commit()
            INGESTION_BATCH_TOTAL.labels(source=source_name, status="success").inc()
        except Exception as exc:
            db.rollback()
            logger.error("Batch transaction failed to commit: %s", exc)
            INGESTION_BATCH_TOTAL.labels(source=source_name, status="error").inc()
            report.errors.append(f"Transaction commit failed: {exc}")

        # Populate alert summaries for report
        for alert in created_alerts:
            report.alert_summaries.append({
                "hazard_type": alert.hazard_type,
                "severity": alert.severity,
                "trigger_value": alert.trigger_value,
                "threshold": alert.threshold,
                "latitude": alert.latitude,
                "longitude": alert.longitude,
            })

        if report.alert_summaries:
            import asyncio
            from ..api.ws import manager
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast_all({
                    "type": "alert",
                    "alerts": report.alert_summaries,
                }))
            except RuntimeError:
                pass

        duration = time.time() - start_time
        report.duration_seconds = round(duration, 3)
        PIPELINE_DURATION_SECONDS.labels(source=source_name).observe(duration)

        logger.info(
            "Ingestion completed for %s: %d total, %d valid, %d rejected, %d alerts in %.2fs",
            source_name,
            report.total_received,
            report.valid_count,
            report.rejected_count,
            report.alerts_generated,
            duration,
        )
        return report

    async def run_connector(self, connector: BaseConnector, db: Session) -> IngestionReport:
        """Fetch from connector and execute full batch ingestion."""
        source = connector.source_name
        fetch_start = time.time()

        try:
            logger.info("Executing connector fetch for %s", source)
            records = await connector.fetch()
            fetch_duration = time.time() - fetch_start
            CONNECTOR_FETCH_TOTAL.labels(source=source, status="success").inc()
            CONNECTOR_LATENCY_SECONDS.labels(source=source).observe(fetch_duration)
        except Exception as exc:
            fetch_duration = time.time() - fetch_start
            CONNECTOR_FETCH_TOTAL.labels(source=source, status="error").inc()
            CONNECTOR_LATENCY_SECONDS.labels(source=source).observe(fetch_duration)
            logger.error("Connector %s failed to fetch data: %s", source, exc)
            return IngestionReport(
                source=source,
                errors=[f"Fetch failed: {exc}"],
                duration_seconds=round(fetch_duration, 3),
            )

        return self.process_batch(records, db, source_name=source)


# Global pipeline instance
ingest_pipeline = IngestPipeline()
