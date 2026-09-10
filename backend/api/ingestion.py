from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CredibilityLog, WeatherObservation
from ..risk_engine.engine import evaluate_observation, serialize_alert
from ..services.validation import add_credibility_log, validate_observation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


def _log_response(log: CredibilityLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "source": log.source,
        "validation_status": log.validation_status,
        "credibility_score": log.credibility_score,
        "error_details": log.error_details,
        "timestamp": log.timestamp.isoformat() if isinstance(log.timestamp, datetime) else log.timestamp,
    }


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_observation(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    result = validate_observation(payload, db)
    log = add_credibility_log(db, payload, result)
    try:
        if result.normalized is None:
            db.commit()
            return {
                "status": result.status,
                "credibility_score": result.score,
                "errors": result.errors,
                "log_id": log.id,
            }

        observation = WeatherObservation(**result.normalized)
        db.add(observation)
        db.flush()
        alerts = evaluate_observation(db, observation)
        db.commit()
        db.refresh(observation)
        db.refresh(log)
        return {
            "status": result.status,
            "credibility_score": result.score,
            "observation_id": observation.id,
            "log_id": log.id,
            "alerts": [serialize_alert(alert) for alert in alerts],
        }
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist weather observation")
        raise HTTPException(status_code=500, detail="Unable to persist ingestion record") from exc


@router.get("/logs")
def get_ingestion_logs(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    try:
        logs = db.query(CredibilityLog).order_by(CredibilityLog.timestamp.desc()).limit(limit).all()
        return [_log_response(log) for log in logs]
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve credibility logs")
        raise HTTPException(status_code=500, detail="Unable to retrieve credibility logs") from exc
