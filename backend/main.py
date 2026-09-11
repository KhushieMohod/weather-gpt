from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from .api.chat import router as chat_router
from .api.ingestion import router as ingestion_router
from .api.risk import router as risk_router
from .api.voice import router as voice_router
from .api.ws import router as ws_router
from .database import Base, SessionLocal, engine
from .risk_engine.engine import scan_recent_observations
from .services.llm_config import validate_llm_environment
from .services.metrics import get_prometheus_metrics
from .services.scheduler import weather_scheduler

logger = logging.getLogger(__name__)


async def _risk_monitor() -> None:
    interval = max(10, int(os.getenv("RISK_SCAN_INTERVAL_SECONDS", "60")))
    while True:
        db = SessionLocal()
        try:
            scan_recent_observations(db)
        except Exception:
            db.rollback()
            logger.exception("Background risk scan failed")
        finally:
            db.close()
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 1. Database migrations / tables
    Base.metadata.create_all(bind=engine)

    # 2. Startup LLM environment inspection
    validate_llm_environment()

    # 3. Scheduled background ingestion jobs
    if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
        weather_scheduler.start()

    # 4. Optional background risk monitor loop
    monitor = None
    if os.getenv("ENABLE_RISK_MONITOR", "false").lower() == "true":
        monitor = asyncio.create_task(_risk_monitor())

    try:
        yield
    finally:
        if monitor:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
        weather_scheduler.shutdown()


app = FastAPI(
    title="WeatherGPT API",
    description="Production Disaster Weather Intelligence & Multi-Source RAG Platform",
    version="0.4.0",
    lifespan=lifespan,
)

# API Routers
app.include_router(ingestion_router)
app.include_router(chat_router)
app.include_router(risk_router)
app.include_router(voice_router)
app.include_router(ws_router)


# Health and Monitoring Endpoints (registered BEFORE static frontend mount)
@app.get("/healthz")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def prometheus_metrics() -> Response:
    """Scrape Prometheus observability metrics."""
    data, content_type = get_prometheus_metrics()
    return Response(content=data, media_type=content_type)


# Mount Static Frontend
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
