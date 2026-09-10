from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage
from ..rag.orchestrator import create_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatQuery(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    user_query: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/query")
def query_chat(payload: ChatQuery, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        orchestrator = create_orchestrator()
        answer = orchestrator.answer(
            db,
            payload.user_query,
            payload.latitude,
            payload.longitude,
        )
        db.add_all(
            [
                ChatMessage(session_id=payload.session_id, role="user", content=payload.user_query),
                ChatMessage(session_id=payload.session_id, role="assistant", content=answer),
            ]
        )
        db.commit()
        return {"session_id": payload.session_id, "answer": answer}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist chat messages")
        raise HTTPException(status_code=500, detail="Unable to persist chat response") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
