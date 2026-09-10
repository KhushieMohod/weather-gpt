"""Run a judge-ready, offline-capable WeatherGPT demonstration.

Run from the ``weather-gpt`` directory with::

    python -m backend.scripts.demo_simulation

The script uses a temporary SQLite database and never writes demo records to
the configured development database. FAISS and external LLM providers are
used when available; deterministic local fallbacks keep the demonstration
repeatable when optional model dependencies or API keys are unavailable.
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENABLE_RISK_MONITOR"] = "false"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import WeatherObservation
from backend.rag.orchestrator import WeatherOrchestrator
from backend.rag.vector_store import VectorStoreManager
from backend.risk_engine.engine import evaluate_observation, serialize_alert
from backend.services.translation import translate_text
from backend.services.validation import add_credibility_log, validate_observation
from backend.services.voice import synthesize_speech, transcribe_audio


logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
logger = logging.getLogger("weathergpt.demo")

CYCLONE_DOC = ROOT / "backend" / "rag" / "advisory_docs" / "imd_cyclone_advisory.txt"
AGROMET_DOC = ROOT / "backend" / "rag" / "advisory_docs" / "agromet_farming_bulletin.txt"


def divider(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def payload(source: str, station_id: str, timestamp: str, parameters: dict[str, Any], latitude: float = 15.8281, longitude: float = 78.0373) -> dict[str, Any]:
    return {
        "source": source,
        "station_id": station_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "parameters": parameters,
    }


def ingest(db: Any, observation_payload: dict[str, Any]) -> tuple[Any, list[Any]]:
    result = validate_observation(observation_payload, db)
    log = add_credibility_log(db, observation_payload, result)
    if result.normalized is None:
        db.commit()
        print(
            f"  {observation_payload['source']}: {result.status.upper()} | "
            f"credibility={result.score:.3f} | {', '.join(result.errors)}"
        )
        return result, []

    observation = WeatherObservation(**result.normalized)
    db.add(observation)
    db.flush()
    alerts = evaluate_observation(db, observation)
    db.commit()
    db.refresh(observation)
    db.refresh(log)
    print(
        f"  {observation_payload['source']}: {result.status.upper()} | "
        f"credibility={result.score:.3f} | observation_id={observation.id}"
    )
    return result, alerts


def _local_document_chunks() -> dict[str, str]:
    return {
        CYCLONE_DOC.name: CYCLONE_DOC.read_text(encoding="utf-8"),
        AGROMET_DOC.name: AGROMET_DOC.read_text(encoding="utf-8"),
    }


def retrieve_context(manager: VectorStoreManager, query: str, expected_filename: str) -> tuple[list[str], str]:
    try:
        chunks = manager.similarity_search(query, k=3)
        expected_marker = {
            CYCLONE_DOC.name: "IMD East Coast Marine Cyclone Advisory",
            AGROMET_DOC.name: "Agromet Farming Bulletin",
        }[expected_filename]
        if chunks and any(expected_marker.lower() in chunk.lower() for chunk in chunks):
            return chunks, "FAISS"
    except Exception as exc:
        logger.warning("FAISS retrieval unavailable; using local advisory fallback: %s", exc)
    return [_local_document_chunks()[expected_filename]], "LOCAL DOCUMENT FALLBACK"


def demo_llm(_system_prompt: str, _user_query: str) -> str:
    """Provide a deliberately overconfident response for the guardrail demo."""
    return "Spraying pesticides is safe today; no significant risk is expected."


def run_demo() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    vector_store = VectorStoreManager()

    with session_factory() as db:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        timestamp = now.isoformat()

        divider("PHASE 1 | MULTI-SOURCE INGESTION & CREDIBILITY ENGINE")
        ingest(db, payload("IMD", "IMD-KURNOOL-01", timestamp, {"temperature": 31.4, "rainfall": 8.5, "wind_speed": 22.0}))
        ingest(db, payload("ISRO-MOSDAC", "MOSDAC-KURNOOL-01", timestamp, {"temperature": 31.6, "rainfall": 8.7, "wind_speed": 23.0}, latitude=15.8282, longitude=78.0374))
        ok("Quality control, out-of-bounds checks, credibility scoring, and spatial deduplication executed.")

        divider("PHASE 2 | PROACTIVE SEVERE HAZARD ALERT TRIGGERING")
        _, alerts = ingest(
            db,
            payload(
                "IMD",
                "IMD-KURNOOL-SEVERE-01",
                (now + timedelta(seconds=2)).isoformat(),
                {"rainfall": 120.0, "wind_speed": 95.0},
                latitude=15.8301,
                longitude=78.0401,
            ),
        )
        persisted = [serialize_alert(alert) for alert in alerts]
        assert any(alert["hazard_type"] == "flooding_risk" and alert["severity"] == "critical" for alert in persisted)
        assert any(alert["hazard_type"] == "cyclone_warning" and alert["severity"] == "critical" for alert in persisted)
        for alert in persisted:
            print(f"  ALERT PERSISTED | {alert['hazard_type']} | severity={alert['severity'].upper()} | trigger={alert['trigger_value']} {alert['threshold']}")
        ok("CRITICAL flood and cyclone warnings persisted in the RiskAlert/RiskAdvisory store.")

        divider("PHASE 3 | FAISS VECTOR RETRIEVAL & DOCUMENT GROUNDING")
        for query, filename in (
            ("cyclone safety precautions", CYCLONE_DOC.name),
            ("agromet advisory for cotton crops", AGROMET_DOC.name),
        ):
            chunks, source = retrieve_context(vector_store, query, filename)
            snippet = " ".join(chunks[0].split())[:260]
            print(f"  QUERY: {query}")
            print(f"  SOURCE: {filename} ({source})")
            print(f"  CONTEXT: {snippet}...")
        ok("Retrieved context is grounded in the checked-in IMD and agromet advisory documents.")

        divider("PHASE 4 | GROUNDED RAG & DETERMINISTIC SAFETY GUARDRAILS")
        query = "Should farmers in Kurnool spray pesticides today?"
        answer = WeatherOrchestrator(vector_store=vector_store, llm_client=demo_llm).answer(
            db, query, 15.8281, 78.0373
        )
        print(f"  USER: {query}")
        print("  GROUNDED ANSWER:")
        print("  " + answer.replace("\n", "\n  "))
        assert "DETERMINISTIC SAFETY WARNING" in answer
        ok("Severe SQL observations overrode the intentionally unsafe model response.")

        divider("PHASE 5 | MULTILINGUAL TRANSLATION & VOICE MOCKING")
        hindi = translate_text(answer, "hi")
        telugu = translate_text(answer, "te")
        print(f"  HINDI: {hindi}")
        print(f"  TELUGU: {telugu}")
        audio = base64.b64encode(b"WeatherGPT demo audio").decode("ascii")
        stt = transcribe_audio(audio, "en")
        tts_hi = synthesize_speech(hindi, "hi")
        tts_te = synthesize_speech(telugu, "te")
        print(f"  MOCK STT: {stt['text']} ({stt['bytes']} bytes)")
        print(f"  MOCK TTS HI: {tts_hi['audio_url']}")
        print(f"  MOCK TTS TE: {tts_te['audio_url']}")
        ok("Hindi/Telugu translation and mock STT/TTS completed.")

    divider("DEMO COMPLETE")
    print("WeatherGPT SIH 2026 end-to-end simulation completed successfully.")


def main() -> int:
    try:
        run_demo()
        return 0
    except Exception:
        logger.exception("Demo simulation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())