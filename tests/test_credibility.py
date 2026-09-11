from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import pytest

TEST_DB_PATH = Path(__file__).resolve().parent / "test_credibility.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import WeatherObservation
from backend.services.credibility import CredibilityFusionEngine, FusedScore


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


def test_source_authority_ranking():
    engine = CredibilityFusionEngine()
    assert engine.calculate_authority("IMD") == 0.95
    assert engine.calculate_authority("ISRO-MOSDAC") == 0.95
    assert engine.calculate_authority("ERA5") == 0.88
    assert engine.calculate_authority("GFS/WRF") == 0.82
    assert engine.calculate_authority("CITIZEN_SENSOR") == 0.60


def test_freshness_decay():
    engine = CredibilityFusionEngine()
    now = datetime.now(timezone.utc)

    fresh = engine.calculate_freshness(now, "IMD", now=now)
    assert fresh == pytest.approx(1.0, 0.01)

    half_life_ago = now - timedelta(hours=3)
    at_half_life = engine.calculate_freshness(half_life_ago, "IMD", now=now)
    assert at_half_life == pytest.approx(0.5, 0.05)

    old = now - timedelta(hours=12)
    at_12h = engine.calculate_freshness(old, "IMD", now=now)
    assert at_12h < 0.10


def test_completeness_calculation():
    engine = CredibilityFusionEngine()
    full_params = {"temperature": 30, "humidity": 60, "rainfall": 0, "wind_speed": 10, "pressure": 1010}
    assert engine.calculate_completeness(full_params) == pytest.approx(1.0)

    sparse_params = {"temperature": 30}
    assert engine.calculate_completeness(sparse_params) < 0.60


def test_conflict_resolution_and_ranking(db_session):
    engine = CredibilityFusionEngine()
    now = datetime.now(timezone.utc)

    obs1 = WeatherObservation(
        source="IMD",
        station_id="STATION-1",
        latitude=19.07,
        longitude=72.87,
        timestamp=now,
        parameters={"temperature": 32.0, "rainfall": 10.0},
    )
    obs2 = WeatherObservation(
        source="GFS/WRF",
        station_id="GFS-NODE-1",
        latitude=19.07,
        longitude=72.87,
        timestamp=now - timedelta(hours=5),
        parameters={"temperature": 30.0, "rainfall": 8.0},
    )
    db_session.add(obs1)
    db_session.add(obs2)
    db_session.commit()

    ranked = engine.resolve_conflicts([obs1, obs2], db_session)
    assert len(ranked) == 2
    # IMD should rank higher due to higher authority and fresher timestamp
    assert ranked[0].observation.source == "IMD"
    assert ranked[0].fused_score.final_score >= ranked[1].fused_score.final_score
