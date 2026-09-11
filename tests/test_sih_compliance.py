"""SIH 2026 prototype compliance checks.

Run from the ``weather-gpt`` directory:

    pip install -r backend/requirements.txt
    pytest tests/test_sih_compliance.py -q

The suite uses a temporary SQLite database. The RAG test exercises the
VectorStoreManager retrieval contract with the real IMD advisory text and a
deterministic in-memory index boundary, so it does not download an embedding
model during CI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

TEST_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = TEST_ROOT / "tests" / "sih-compliance.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE.as_posix()}"
os.environ["ENABLE_RISK_MONITOR"] = "false"
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import RiskAlert
from backend.rag.vector_store import VectorStoreManager
from backend.services.validation import validate_observation


@pytest.fixture(scope="module")
def db_session():
    if TEST_DATABASE.exists():
        try:
            TEST_DATABASE.unlink()
        except OSError:
            pass
    engine = create_engine(
        f"sqlite:///{TEST_DATABASE.as_posix()}",
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
            if TEST_DATABASE.exists():
                TEST_DATABASE.unlink()
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


def test_extreme_temperature_is_rejected_with_credibility_penalty(db_session):
    result = validate_observation(
        {
            "source": "IMD",
            "station_id": "SIH-TEST-01",
            "latitude": 19.076,
            "longitude": 72.8777,
            "timestamp": "2026-09-10T12:00:00+00:00",
            "parameters": {"temperature": 65.0, "humidity": 55},
        },
        db_session,
    )

    assert result.status == "rejected"
    assert "temperature exceeds 60 C" in result.errors
    assert result.score < 0.95
    assert result.score == pytest.approx(0.475)


def test_vector_store_retrieves_imd_cyclone_advisory(tmp_path, monkeypatch):
    advisory_path = TEST_ROOT / "backend" / "rag" / "advisory_docs" / "imd_cyclone_advisory.txt"
    advisory_text = advisory_path.read_text(encoding="utf-8")
    index_dir = tmp_path / "vector_db"
    index_dir.mkdir()
    (index_dir / "advisories.faiss").write_bytes(b"deterministic-test-index")
    (index_dir / "metadata.json").write_text(
        json.dumps([{"text": advisory_text, "source": advisory_path.name}]),
        encoding="utf-8",
    )

    class DeterministicIndex:
        ntotal = 1

        def search(self, _embedding: Any, _count: int) -> tuple[None, list[list[int]]]:
            return None, [[0]]

    class DeterministicModel:
        def encode(self, _queries: list[str], **_kwargs: Any) -> list[list[float]]:
            return [[1.0]]

    manager = VectorStoreManager(index_dir=index_dir)
    monkeypatch.setattr(manager, "_load_model", lambda: DeterministicModel())
    monkeypatch.setattr(manager, "_load_persisted", lambda: _load_test_index(manager, DeterministicIndex(), index_dir))

    chunks = manager.similarity_search("cyclone safety for coastal fishing vessels", k=3)

    assert chunks
    assert "IMD East Coast Marine Cyclone Advisory" in chunks[0]
    assert "fishing vessels should not venture" in chunks[0]


def _load_test_index(manager: VectorStoreManager, index: Any, index_dir: Path) -> None:
    manager._index = index
    manager._metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))


def test_critical_flood_alert_is_generated_for_120_mm_rainfall(client, db_session):
    response = client.post(
        "/api/ingestion/submit",
        json={
            "source": "IMD",
            "station_id": "SIH-FLOOD-01",
            "latitude": 19.076,
            "longitude": 72.8777,
            "timestamp": "2026-09-10T13:00:00+00:00",
            "parameters": {"rainfall": 120.0},
        },
    )

    assert response.status_code == 201
    alert = db_session.query(RiskAlert).filter_by(hazard_type="flooding_risk").one()
    assert alert.severity == "critical"
    assert alert.trigger_value == pytest.approx(120.0)


def test_api_health_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}