from __future__ import annotations

import base64
import pytest

from backend.services.voice import synthesize_speech, transcribe_audio


def test_transcribe_audio_validation():
    with pytest.raises(ValueError, match="audio_base64 is required"):
        transcribe_audio("")

    with pytest.raises(ValueError, match="audio_base64 is invalid"):
        transcribe_audio("not-base-64!!")


def test_transcribe_audio_mock_fallback():
    dummy_wav = base64.b64encode(b"RIFFdummywavebytes").decode("ascii")
    result = transcribe_audio(f"data:audio/wav;base64,{dummy_wav}", language="hi")
    assert result["mock"] is True
    assert result["language"] == "hi"
    assert "weather" in result["text"].lower()


def test_synthesize_speech_mock_fallback():
    result = synthesize_speech("Warning: Heavy rainfall alert in Mumbai", language="hi")
    assert result["mock"] is True
    assert result["language"] == "hi"
    assert "/api/voice/audio/" in result["audio_url"]
