from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.voice import synthesize_speech, transcribe_audio

router = APIRouter(prefix="/api/voice", tags=["voice"])


class AudioInput(BaseModel):
    audio_base64: str = Field(min_length=1)
    language: str = "en"


class SpeechInput(BaseModel):
    text: str = Field(min_length=1)
    language: str = "en"


@router.post("/transcribe")
def transcribe(payload: AudioInput) -> dict[str, Any]:
    try:
        return transcribe_audio(payload.audio_base64, payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/synthesize")
def synthesize(payload: SpeechInput) -> dict[str, Any]:
    return synthesize_speech(payload.text, payload.language)