from __future__ import annotations

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ChatMessage
from backend.services.translation import (
    detect_language,
    normalize_language,
    save_chat_message,
    translate_text,
)

TEST_DB_PATH = Path(__file__).resolve().parent / "test_trans.sqlite3"


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


def test_normalize_language():
    assert normalize_language("hi-IN") == "hi"
    assert normalize_language("TE") == "te"
    assert normalize_language("ta-LK") == "ta"
    assert normalize_language("mr") == "mr"
    assert normalize_language("fr") == "en"  # unsupported falls back to en
    assert normalize_language(None) == "en"


def test_detect_language():
    assert detect_language("मौसम चेतावनी जारी") == "hi"
    assert detect_language("వాతావరణ సమాచారం") == "te"
    assert detect_language("வானிலை அறிக்கை") == "ta"
    assert detect_language("Heavy rain in Mumbai") == "en"


def test_translate_text_dictionary_fallback():
    hi = translate_text("Weather alert. Please stay safe.", "hi")
    assert "मौसम चेतावनी" in hi
    assert "कृपया सुरक्षित रहें" in hi

    te = translate_text("Weather alert. Please stay safe.", "te")
    assert "వాతావరణ హెచ్చరిక" in te
    assert "దయచేసి సురక్షితంగా ఉండండి" in te

    ta = translate_text("Weather alert. Please stay safe.", "ta")
    assert "வானிலை எச்சரிக்கை" in ta

    mr = translate_text("Weather alert. Please stay safe.", "mr")
    assert "हवामान इशारा" in mr

    en = translate_text("Weather alert. Please stay safe.", "en")
    assert en == "Weather alert. Please stay safe."


def test_save_chat_message(db_session):
    msg = save_chat_message(
        db=db_session,
        session_id="test-session-1",
        role="user",
        content="What is the weather in Delhi?",
        language="hi-IN",
    )
    db_session.commit()
    assert msg.id is not None
    assert msg.language == "hi"
    assert msg.role == "user"
