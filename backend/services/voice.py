from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Any


def transcribe_audio(audio_base64: str, language: str = "en") -> dict[str, Any]:
    """Validate audio input and return deterministic mock STT text."""
    if not audio_base64:
        raise ValueError("audio_base64 is required")
    encoded = audio_base64.split(",", 1)[-1]
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("audio_base64 is invalid") from exc
    if not audio:
        raise ValueError("audio stream is empty")
    return {
        "text": "Please check the current weather risk near my location.",
        "language": language,
        "mock": True,
        "bytes": len(audio),
    }


def synthesize_speech(text: str, language: str = "en") -> dict[str, Any]:
    """Return a stable mock audio URL until a regional TTS provider is configured."""
    digest = hashlib.sha256(f"{language}:{text}".encode("utf-8")).hexdigest()[:16]
    return {
        "audio_url": f"/api/voice/audio/{digest}.wav",
        "language": language,
        "mock": True,
        "text": text,
    }