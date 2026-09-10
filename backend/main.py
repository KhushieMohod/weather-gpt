import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.chat import router as chat_router
from .api.ingestion import router as ingestion_router
from .api.risk import router as risk_router
from .api.voice import router as voice_router
from .api.ws import router as ws_router
from .database import Base, SessionLocal, engine
from .risk_engine.engine import scan_recent_observations

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
    Base.metadata.create_all(bind=engine)
    monitor = None
    if os.getenv("ENABLE_RISK_MONITOR", "false").lower() == "true":
        monitor = asyncio.create_task(_risk_monitor())
    try:
        yield
    finally:
        if monitor:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)

app = FastAPI(title="WeatherGPT API", version="0.3", lifespan=lifespan)
app.include_router(ingestion_router)
app.include_router(chat_router)
app.include_router(risk_router)
app.include_router(voice_router)
app.include_router(ws_router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/healthz")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
