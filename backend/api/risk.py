from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RiskAlert
from ..risk_engine.engine import scan_recent_observations, serialize_alert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/scan")
def scan_risks(
    lookback_minutes: int = Query(default=180, ge=1, le=10080),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        alerts = scan_recent_observations(db, lookback_minutes)
        return {"alerts_created": len(alerts), "alerts": [serialize_alert(alert) for alert in alerts]}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Risk scan failed")
        raise HTTPException(status_code=500, detail="Unable to scan recent observations") from exc


@router.get("/alerts")
def get_alerts(
    status: str = Query(default="active", pattern="^(active|resolved|all)$"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    try:
        query = db.query(RiskAlert).order_by(RiskAlert.created_at.desc()).limit(limit)
        if status != "all":
            query = query.filter(RiskAlert.status == status)
        return [serialize_alert(alert) for alert in query.all()]
    except SQLAlchemyError as exc:
        logger.exception("Failed to retrieve risk alerts")
        raise HTTPException(status_code=500, detail="Unable to retrieve risk alerts") from exc