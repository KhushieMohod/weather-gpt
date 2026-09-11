from __future__ import annotations

import base64
import binascii
import hashlib
import io
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Regional Indian language voice code mappings for Google Text-to-Speech
INDIAN_VOICES = {
    "hi": {"language_code": "hi-IN", "name": "hi-IN-Neural2-A"},
    "te": {"language_code": "te-IN", "name": "te-IN-Standard-A"},
    "ta": {"language_code": "ta-IN", "name": "ta-IN-Standard-A"},
    "mr": {"language_code": "mr-IN", "name": "mr-IN-Standard-A"},
    "bn": {"language_code": "bn-IN", "name": "bn-IN-Standard-A"},
    "en": {"language_code": "en-IN", "name": "en-IN-Neural2-A"},
}


class WhisperSTTAdapter:
    """OpenAI Whisper API speech-to-text adapter."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:
                logger.debug("Whisper client failed to initialize: %s", exc)

    def transcribe(self, audio_bytes: bytes, language: str) -> str:
        if not self._client:
            raise RuntimeError("OpenAI client not configured for Whisper STT")

        # Package raw audio in a named buffer for OpenAI API
        buffer = io.BytesIO(audio_bytes)
        buffer.name = "audio.wav"

        lang_code = language.split("-")[0]
        params: dict[str, Any] = {
            "model": "whisper-1",
            "file": buffer,
        }
        if lang_code in {"en", "hi", "te", "ta", "mr", "bn", "gu"}:
            params["language"] = lang_code

        response = self._client.audio.transcriptions.create(**params)
        return response.text


class GoogleTTSAdapter:
    """Google Cloud Text-to-Speech adapter with Indian language neural voices."""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        try:
            from google.cloud import texttospeech
            self._client = texttospeech.TextToSpeechClient()
            self._available = True
        except Exception as exc:
            logger.debug("Google Cloud TTS client not available: %s", exc)

    def synthesize(self, text: str, language: str) -> bytes:
        if not self._available or not self._client:
            raise RuntimeError("Google Cloud TTS client not configured")

        from google.cloud import texttospeech

        lang_key = language.split("-")[0]
        voice_cfg = INDIAN_VOICES.get(lang_key, INDIAN_VOICES["en"])

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["name"],
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return response.audio_content


def transcribe_audio(audio_base64: str, language: str = "en") -> dict[str, Any]:
    """Validate audio input and transcribe via Whisper or regional fallback."""
    if not audio_base64:
        raise ValueError("audio_base64 is required")
    encoded = audio_base64.split(",", 1)[-1]
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("audio_base64 is invalid") from exc
    if not audio:
        raise ValueError("audio stream is empty")

    provider = os.getenv("STT_PROVIDER", "mock").lower()

    if provider == "whisper" and os.getenv("OPENAI_API_KEY"):
        try:
            adapter = WhisperSTTAdapter()
            text = adapter.transcribe(audio, language)
            return {
                "text": text,
                "language": language,
                "provider": "whisper",
                "mock": False,
                "bytes": len(audio),
            }
        except Exception as exc:
            logger.warning("Whisper transcription failed (%s), falling back to mock text", exc)

    # Deterministic fallback response for offline testing
    return {
        "text": "Please check the current weather risk near my location.",
        "language": language,
        "mock": True,
        "bytes": len(audio),
    }


def synthesize_speech(text: str, language: str = "en") -> dict[str, Any]:
    """Synthesize speech audio via Google TTS or provide deterministic audio URL."""
    provider = os.getenv("TTS_PROVIDER", "mock").lower()

    if provider == "google":
        try:
            adapter = GoogleTTSAdapter()
            audio_bytes = adapter.synthesize(text, language)
            b64_audio = base64.b64encode(audio_bytes).decode("ascii")
            return {
                "audio_base64": f"data:audio/wav;base64,{b64_audio}",
                "language": language,
                "provider": "google",
                "mock": False,
                "text": text,
            }
        except Exception as exc:
            logger.warning("Google Cloud TTS failed (%s), falling back to URL stub", exc)

    digest = hashlib.sha256(f"{language}:{text}".encode("utf-8")).hexdigest()[:16]
    return {
        "audio_url": f"/api/voice/audio/{digest}.wav",
        "language": language,
        "mock": True,
        "text": text,
    }