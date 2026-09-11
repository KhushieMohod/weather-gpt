from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.orm import Session

from ..models import ChatMessage

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta", "mr", "bn", "gu", "kn", "ml", "pa"}

# Comprehensive multilingual weather & safety terminology dictionary for fallback
_PHRASES: dict[str, dict[str, str]] = {
    "hi": {
        "Weather alert": "मौसम चेतावनी",
        "Please stay safe.": "कृपया सुरक्षित रहें।",
        "Cyclone Alert": "चक्रवात चेतावनी",
        "Severe Flooding Risk": "गंभीर बाढ़ का खतरा",
        "High Wind Warning": "तेज हवा की चेतावनी",
        "Extreme Heat Advisory": "अत्यधिक गर्मी की सलाह",
        "Evacuate to higher ground immediately.": "तुरंत ऊंचे स्थानों पर जाएं।",
        "Fishermen should not venture into the sea.": "मछुआरों को समुद्र में नहीं जाना चाहिए।",
        "Current temperature": "वर्तमान तापमान",
        "Rainfall": "वर्षा",
        "Wind speed": "हवा की गति",
        "Safe": "सुरक्षित",
        "Hazard Warning": "खतरा चेतावनी",
    },
    "te": {
        "Weather alert": "వాతావరణ హెచ్చరిక",
        "Please stay safe.": "దయచేసి సురక్షితంగా ఉండండి.",
        "Cyclone Alert": "తుఫాను హెచ్చరిక",
        "Severe Flooding Risk": "తీవ్రమైన వరద ప్రమాదం",
        "High Wind Warning": "తీవ్రమైన గాలుల హెచ్చరిక",
        "Extreme Heat Advisory": "తీవ్రమైన ఎండల హెచ్చరిక",
        "Evacuate to higher ground immediately.": "వెంటనే ఎత్తైన ప్రదేశాలకు వెళ్లండి.",
        "Fishermen should not venture into the sea.": "మత్స్యకారులు సముద్రంలోకి వెళ్లవద్దు.",
        "Current temperature": "ప్రస్తుత ఉష్ణోగ్రత",
        "Rainfall": "వర్షపాతం",
        "Wind speed": "గాలి వేగం",
        "Safe": "సురక్షితం",
        "Hazard Warning": "ప్రమాద హెచ్చరిక",
    },
    "ta": {
        "Weather alert": "வானிலை எச்சரிக்கை",
        "Please stay safe.": "தயவுசெய்து பாதுகாப்பாக இருங்கள்.",
        "Cyclone Alert": "புயல் எச்சரிக்கை",
        "Severe Flooding Risk": "கடுமையான வெள்ள அபாயம்",
        "High Wind Warning": "பலத்த காற்று எச்சரிக்கை",
        "Extreme Heat Advisory": "கடும் வெப்ப எச்சரிக்கை",
        "Evacuate to higher ground immediately.": "உடனடியாக உயரமான இடங்களுக்கு செல்லுங்கள்.",
        "Fishermen should not venture into the sea.": "மீனவர்கள் கடலுக்குள் செல்ல வேண்டாம்.",
        "Current temperature": "தற்போதைய வெப்பநிலை",
        "Rainfall": "மழைப்பொழிவு",
        "Wind speed": "காற்றின் வேகம்",
        "Safe": "பாதுகாப்பானது",
        "Hazard Warning": "அபாய எச்சரிக்கை",
    },
    "mr": {
        "Weather alert": "हवामान इशारा",
        "Please stay safe.": "कृपया सुरक्षित रहा.",
        "Cyclone Alert": "चक्रीवादळ इशारा",
        "Severe Flooding Risk": "गंभीर पुराचा धोका",
        "High Wind Warning": "जोरदार वाऱ्याचा इशारा",
        "Extreme Heat Advisory": "तीव्र उष्णतेचा सल्ला",
        "Evacuate to higher ground immediately.": "त्वरित उंच ठिकाणी सुरक्षित जा.",
        "Fishermen should not venture into the sea.": "मासेमारांनी समुद्रात जाऊ नये.",
        "Current temperature": "सध्याचे तापमान",
        "Rainfall": "पाऊस",
        "Wind speed": "वाऱ्याचा वेग",
        "Safe": "सुरक्षित",
        "Hazard Warning": "धोक्याची सूचना",
    },
}


class GoogleTranslateAdapter:
    """Google Cloud Translation API v3 integration with error handling."""

    def __init__(self, project_id: str | None = None) -> None:
        self.project_id = project_id or os.getenv("GOOGLE_TRANSLATE_PROJECT_ID")
        self._client = None
        self._available = False
        try:
            from google.cloud import translate_v3
            if self.project_id:
                self._client = translate_v3.TranslationServiceClient()
                self._available = True
        except Exception as exc:
            logger.debug("Google Cloud Translation client not initialized: %s", exc)

    def translate(self, text: str, target_language: str, source_language: str = "en") -> str:
        if not self._available or not self._client or not self.project_id:
            raise RuntimeError("Google Cloud Translation not configured")

        from google.cloud import translate_v3
        parent = f"projects/{self.project_id}/locations/global"
        response = self._client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source_language,
                "target_language_code": target_language,
            }
        )
        if response.translations:
            return response.translations[0].translated_text
        return text


class LocalTranslateAdapter:
    """Stub adapter for local IndicTrans2 / MarianMT neural models."""

    def __init__(self) -> None:
        self._model_loaded = False

    def translate(self, text: str, target_language: str) -> str:
        # Fallback to dictionary if neural weights are not downloaded locally
        raise NotImplementedError("Local translation model weights not loaded")


def normalize_language(language: str | None) -> str:
    """Normalize language tags like 'hi-IN' or 'HI' to standard ISO 639-1 code."""
    code = (language or "en").lower().split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else "en"


def detect_language(text: str) -> str:
    """Heuristic / Unicode block detection for Indic languages."""
    for char in text:
        cp = ord(char)
        if 0x0900 <= cp <= 0x097F:
            return "hi"  # Devanagari (Hindi/Marathi)
        if 0x0C00 <= cp <= 0x0C7F:
            return "te"  # Telugu
        if 0x0B80 <= cp <= 0x0BFF:
            return "ta"  # Tamil
        if 0x0980 <= cp <= 0x09FF:
            return "bn"  # Bengali
        if 0x0A80 <= cp <= 0x0AFF:
            return "gu"  # Gujarati
    return "en"


_google_adapter: GoogleTranslateAdapter | None = None


def translate_text(text: str, target_language: str = "en") -> str:
    """Translate text to target language with fallback chain:
    1. Google Cloud Translation (if provider is configured)
    2. Multilingual phrase dictionary replacement
    3. Prefixed tag fallback
    """
    global _google_adapter
    language = normalize_language(target_language)
    if language == "en" or not text.strip():
        return text

    provider = os.getenv("TRANSLATION_PROVIDER", "mock").lower()

    if provider == "google":
        if _google_adapter is None:
            _google_adapter = GoogleTranslateAdapter()
        try:
            return _google_adapter.translate(text, language)
        except Exception as exc:
            logger.warning("Google translation failed (%s), falling back to offline lexicon", exc)

    # Fallback to phrase replacement dictionary
    translated = text
    phrases = _PHRASES.get(language, {})
    for source, target in phrases.items():
        translated = translated.replace(source, target)

    if translated != text:
        return translated

    # If no phrases matched in offline fallback mode
    return f"[{language}] {text}"


def save_chat_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    language: str = "en",
) -> ChatMessage:
    """Persist chat history with normalized language tag."""
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        language=normalize_language(language),
    )
    db.add(message)
    return message