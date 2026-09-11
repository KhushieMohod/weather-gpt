from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..connectors import ERA5Connector, GFSConnector, IMDConnector, MOSDACConnector, get_connector
from ..database import SessionLocal
from .pipeline import IngestionReport, ingest_pipeline

logger = logging.getLogger(__name__)


class WeatherScheduler:
    """Manages scheduled background data ingestion jobs for all weather sources."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_runs: dict[str, dict[str, Any]] = {}

    def _parse_trigger(self, cron_str: str, default_minutes: int) -> CronTrigger | IntervalTrigger:
        """Parse cron expression or fall back to interval trigger."""
        cron_str = cron_str.strip()
        parts = cron_str.split()
        if len(parts) == 5:
            try:
                return CronTrigger.from_crontab(cron_str)
            except Exception as exc:
                logger.warning("Invalid cron string '%s' (%s), using interval %d min", cron_str, exc, default_minutes)
        return IntervalTrigger(minutes=default_minutes)

    async def _run_job(self, source_name: str, connector_cls: Any) -> IngestionReport:
        """Execute a scheduled connector fetch job."""
        logger.info("Executing scheduled ingestion job for %s", source_name)
        connector = connector_cls()
        db = SessionLocal()
        start_ts = datetime.now(timezone.utc).isoformat()
        try:
            report = await ingest_pipeline.run_connector(connector, db)
            self.last_runs[source_name] = {
                "timestamp": start_ts,
                "status": "success" if not report.errors else "partial_error",
                "valid_records": report.valid_count,
                "rejected_records": report.rejected_count,
                "alerts_generated": report.alerts_generated,
                "duration_seconds": report.duration_seconds,
            }
            return report
        except Exception as exc:
            logger.exception("Scheduled ingestion job for %s failed", source_name)
            self.last_runs[source_name] = {
                "timestamp": start_ts,
                "status": "failed",
                "error": str(exc),
            }
            return IngestionReport(source=source_name, errors=[str(exc)])
        finally:
            await connector.close()
            db.close()

    def start(self) -> None:
        """Register jobs and start scheduler."""
        if self.is_running:
            return

        # IMD: Default every 15 minutes
        imd_cron = os.getenv("IMD_FETCH_CRON", "*/15 * * * *")
        self.scheduler.add_job(
            self._run_job,
            trigger=self._parse_trigger(imd_cron, default_minutes=15),
            args=["IMD", IMDConnector],
            id="job_imd_fetch",
            name="IMD Surface AWS Observations",
            replace_existing=True,
        )

        # MOSDAC: Default every 30 minutes
        mosdac_cron = os.getenv("MOSDAC_FETCH_CRON", "*/30 * * * *")
        self.scheduler.add_job(
            self._run_job,
            trigger=self._parse_trigger(mosdac_cron, default_minutes=30),
            args=["ISRO-MOSDAC", MOSDACConnector],
            id="job_mosdac_fetch",
            name="ISRO MOSDAC INSAT-3D Satellite Products",
            replace_existing=True,
        )

        # GFS: Default every 6 hours
        gfs_cron = os.getenv("GFS_FETCH_CRON", "0 */6 * * *")
        self.scheduler.add_job(
            self._run_job,
            trigger=self._parse_trigger(gfs_cron, default_minutes=360),
            args=["GFS/WRF", GFSConnector],
            id="job_gfs_fetch",
            name="NOAA GFS Numerical Forecasts",
            replace_existing=True,
        )

        # ERA5: Default daily at 06:00 UTC
        era5_cron = os.getenv("ERA5_FETCH_CRON", "0 6 * * *")
        self.scheduler.add_job(
            self._run_job,
            trigger=self._parse_trigger(era5_cron, default_minutes=1440),
            args=["ERA5", ERA5Connector],
            id="job_era5_fetch",
            name="ECMWF ERA5 Climate Reanalysis",
            replace_existing=True,
        )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.scheduler.start()
        self.is_running = True
        logger.info("Production weather ingestion scheduler started successfully with 4 connector jobs")

    def shutdown(self) -> None:
        """Gracefully shut down background scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Production weather scheduler shut down")

    async def trigger_now(self, source_name: str) -> IngestionReport:
        """Manually trigger immediate execution of a connector."""
        connector = get_connector(source_name)
        db = SessionLocal()
        try:
            return await ingest_pipeline.run_connector(connector, db)
        finally:
            await connector.close()
            db.close()

    def get_status(self) -> dict[str, Any]:
        """Return the status of active jobs, next run times, and execution telemetry."""
        jobs_info = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
                jobs_info.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": next_run,
                })

        return {
            "scheduler_running": self.is_running,
            "job_count": len(jobs_info),
            "jobs": jobs_info,
            "last_executions": self.last_runs,
        }


# Global scheduler singleton
weather_scheduler = WeatherScheduler()
