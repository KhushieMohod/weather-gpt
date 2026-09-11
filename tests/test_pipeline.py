from datetime import datetime, timezone
from pathlib import Path
import os
import pytest

TEST_DB_PATH = Path(__file__).resolve().parent / "test_pipeline.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["ENABLE_RISK_MONITOR"] = "false"
os.environ["ENABLE_SCHEDULER"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import RiskAlert, WeatherObservation
from backend.services.pipeline import IngestPipeline, ingest_pipeline
from backend.services.scheduler import weather_scheduler


@pytest.fixture(scope="module")
def db_session():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass
    engine = create_engine(
        f"sqlite:///{TEST_DB_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        try:
            if TEST_DB_PATH.exists():
                TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_pipeline_process_batch_with_valid_and_invalid(db_session):
    records = [
        {
            "source": "IMD",
            "station_id": "BATCH-TEST-1",
            "latitude": 28.58,
            "longitude": 77.20,
            "timestamp": "2026-09-11T10:00:00+00:00",
            "parameters": {"temperature": 33.0, "rainfall": 15.0},
        },
        {
            "source": "IMD",
            "station_id": "BATCH-TEST-INVALID",
            "latitude": 28.58,
            "longitude": 77.20,
            "timestamp": "2026-09-11T10:05:00+00:00",
            "parameters": {"temperature": 75.0},  # exceeds 60C
        },
        {
            "source": "GFS/WRF",
            "station_id": "BATCH-TEST-FLOOD",
            "latitude": 19.07,
            "longitude": 72.87,
            "timestamp": "2026-09-11T10:10:00+00:00",
            "parameters": {"rainfall": 115.0},  # triggers flooding risk
        },
    ]

    report = ingest_pipeline.process_batch(records, db_session, source_name="test-batch")
    assert report.total_received == 3
    assert report.valid_count == 2
    assert report.rejected_count == 1
    assert report.alerts_generated >= 1
    assert len(report.alert_summaries) >= 1


def test_batch_api_endpoint(client):
    response = client.post(
        "/api/ingestion/batch",
        json=[
            {
                "source": "IMD",
                "station_id": "API-BATCH-1",
                "latitude": 13.08,
                "longitude": 80.27,
                "timestamp": "2026-09-11T11:00:00+00:00",
                "parameters": {"temperature": 32.0, "rainfall": 20.0},
            }
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_received"] == 1
    assert data["valid_count"] == 1


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    weather_scheduler.start()
    assert weather_scheduler.is_running is True
    status = weather_scheduler.get_status()
    assert status["scheduler_running"] is True
    assert status["job_count"] == 4

    weather_scheduler.shutdown()
    assert weather_scheduler.is_running is False


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "weathergpt_" in response.text
