from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models import RiskAlert, WeatherObservation
from .rules import RiskRule, triggered_rules

logger = logging.getLogger(__name__)


def _alert_exists(db: Session, observation: WeatherObservation, hazard_type: str) -> bool:
    return (
        db.query(RiskAlert)
        .filter(
            RiskAlert.observation_id == observation.id,
            RiskAlert.hazard_type == hazard_type,
        )
        .first()
        is not None
    )


def evaluate_observation(db: Session, observation: WeatherObservation) -> list[RiskAlert]:
    """Create idempotent alerts for threshold breaches in one observation."""
    alerts: list[RiskAlert] = []
    for rule, value in triggered_rules(observation.parameters):
        if _alert_exists(db, observation, rule.hazard_type):
            continue
        alert = RiskAlert(
            observation_id=observation.id,
            hazard_type=rule.hazard_type,
            severity=rule.severity,
            source=observation.source,
            latitude=observation.latitude,
            longitude=observation.longitude,
            trigger_value=value,
            threshold=rule.threshold,
            audiences=list(rule.audiences),
            recommendations=rule.recommendations,
            observed_at=observation.timestamp,
        )
        db.add(alert)
        alerts.append(alert)
        logger.warning(
            "Risk alert: %s=%s exceeded %s at (%s, %s)",
            rule.hazard_type, value, rule.threshold, observation.latitude, observation.longitude,
        )
    return alerts


def scan_recent_observations(db: Session, lookback_minutes: int = 180) -> list[RiskAlert]:
    since = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    observations = (
        db.query(WeatherObservation)
        .filter(WeatherObservation.timestamp >= since)
        .order_by(WeatherObservation.timestamp.desc())
        .all()
    )
    alerts = [alert for observation in observations for alert in evaluate_observation(db, observation)]
    if alerts:
        db.commit()
        for alert in alerts:
            db.refresh(alert)
    return alerts


def serialize_alert(alert: RiskAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "observation_id": alert.observation_id,
        "hazard_type": alert.hazard_type,
        "severity": alert.severity,
        "source": alert.source,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "trigger_value": alert.trigger_value,
        "threshold": alert.threshold,
        "audiences": alert.audiences,
        "recommendations": alert.recommendations,
        "status": alert.status,
        "observed_at": alert.observed_at.isoformat(),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }