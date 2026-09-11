from __future__ import annotations

import io
import math
import struct
from typing import Any

from fastapi import APIRouter, HTTPException, Response
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


@router.get("/audio/{digest}.wav")
def get_audio(digest: str) -> Response:
    """Serve a deterministic audio WAV stream for synthesized voice prompts."""
    sample_rate = 16000
    duration_secs = 0.5
    num_samples = int(sample_rate * duration_secs)
    buffer = io.BytesIO()
    # Write canonical RIFF WAV header
    buffer.write(b"RIFF")
    buffer.write(struct.pack("<I", 36 + num_samples * 2))
    buffer.write(b"WAVEfmt ")
    buffer.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buffer.write(b"data")
    buffer.write(struct.pack("<I", num_samples * 2))
    # Write synthetic audio tone
    for i in range(num_samples):
        val = int(2500 * math.sin(2 * math.pi * 440 * i / sample_rate))
        buffer.write(struct.pack("<h", val))
    return Response(content=buffer.getvalue(), media_type="audio/wav")