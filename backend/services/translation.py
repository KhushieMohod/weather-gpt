from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import ChatMessage

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta", "mr"}

# Small deterministic fallback for the prototype. Replace translate_text with
# an API/library adapter without changing the WebSocket or database contract.
_PHRASES: dict[str, dict[str, str]] = {
    "hi": {"Weather alert": "मौसम चेतावनी", "Please stay safe.": "कृपया सुरक्षित रहें।"},
    "te": {"Weather alert": "వాతావరణ హెచ్చరిక", "Please stay safe.": "దయచేసి సురక్షితంగా ఉండండి."},
    "ta": {"Weather alert": "வானிலை எச்சரிக்கை", "Please stay safe.": "தயவுசெய்து பாதுகாப்பாக இருங்கள்."},
    "mr": {"Weather alert": "हवामान इशारा", "Please stay safe.": "कृपया सुरक्षित रहा."},
}


def normalize_language(language: str | None) -> str:
    code = (language or "en").lower().split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else "en"


def translate_text(text: str, target_language: str = "en") -> str:
    language = normalize_language(target_language)
    if language == "en":
        return text
    translated = text
    for source, target in _PHRASES[language].items():
        translated = translated.replace(source, target)
    if translated == text:
        return f"[{language}] {text}"
    return translated


def save_chat_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    language: str = "en",
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        language=normalize_language(language),
    )
    db.add(message)
    return message