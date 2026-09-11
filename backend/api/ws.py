from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.exc import SQLAlchemyError

from ..database import SessionLocal
from ..rag.orchestrator import create_orchestrator
from ..services.translation import normalize_language, save_chat_message, translate_text

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        from ..services.metrics import ACTIVE_CHAT_SESSIONS
        await websocket.accept()
        self.active.setdefault(session_id, set()).add(websocket)
        total = sum(len(sockets) for sockets in self.active.values())
        ACTIVE_CHAT_SESSIONS.set(total)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        from ..services.metrics import ACTIVE_CHAT_SESSIONS
        connections = self.active.get(session_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.active.pop(session_id, None)
        total = sum(len(sockets) for sockets in self.active.values())
        ACTIVE_CHAT_SESSIONS.set(total)

    async def broadcast_all(self, message: dict[str, Any]) -> None:
        for session_id, sockets in list(self.active.items()):
            for ws in list(sockets):
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


async def _stream_blocks(websocket: WebSocket, text: str, block_size: int = 36) -> None:
    for index in range(0, len(text), block_size):
        await websocket.send_json({"type": "token", "text": text[index:index + block_size]})
        await asyncio.sleep(0.02)


@router.websocket("/api/ws/chat/{session_id}")
async def chat_socket(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"user_query": raw}

            query = str(payload.get("user_query", "")).strip()
            if not query:
                await websocket.send_json({"type": "error", "detail": "user_query is required"})
                continue
            language = normalize_language(payload.get("language"))
            latitude = float(payload.get("latitude", 28.6139))
            longitude = float(payload.get("longitude", 77.2090))
            db = SessionLocal()
            try:
                answer = create_orchestrator().answer(db, query, latitude, longitude)
                localized_answer = translate_text(answer, language)
                save_chat_message(db, session_id, "user", query, language)
                save_chat_message(db, session_id, "assistant", localized_answer, language)
                db.commit()
            except (SQLAlchemyError, ValueError) as exc:
                db.rollback()
                logger.exception("WebSocket chat request failed")
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            finally:
                db.close()

            await websocket.send_json({"type": "start", "language": language})
            await _stream_blocks(websocket, localized_answer)
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected: %s", session_id)
    except Exception:
        logger.exception("Unexpected WebSocket failure: %s", session_id)
    finally:
        manager.disconnect(session_id, websocket)