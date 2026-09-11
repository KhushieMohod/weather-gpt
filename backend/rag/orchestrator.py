from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import WeatherObservation
from ..risk_engine.rules import RiskRule, triggered_rules
from .vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are WeatherGPT, an expert agricultural and disaster advisor.
Ground your response strictly on this validated weather data: {weather_data}
and the following official meteorological advisory bulletins: {retrieved_context}.
RULE: Never alter numerical values or issue warnings that contradict the provided SQL weather observations.
Do not hallucinate or use external assumptions. If information is missing, state it honestly. Give action-oriented advice."""

LLMCallable = Callable[[str, str], str]

LLM_ERROR_MESSAGE = (
    "WeatherGPT could not reach the configured language model. "
    "The grounded weather and advisory context was retrieved, but no generated response is available. "
    "Check LLM_PROVIDER and the corresponding API key or provider quota."
)

SAFETY_CHECK_FAILED_MESSAGE = (
    "DETERMINISTIC SAFETY NOTICE: The generated weather response could not be safely validated. "
    "Do not rely on it for a severe-weather decision. Check the latest official IMD advisory "
    "and local emergency guidance."
)

_HAZARD_TERMS: dict[str, tuple[str, ...]] = {
    "heavy_rainfall": ("heavy rainfall", "heavy rain", "flood", "waterlogging"),
    "extreme_heat": ("extreme heat", "heatwave", "heat wave", "dangerous heat"),
    "dangerous_wind": ("dangerous wind", "strong wind", "high wind", "gale", "windstorm"),
    "flooding_risk": ("flood", "flash flood", "flooding", "inundation"),
}
_ADVISORY_TERMS = (
    "warning",
    "alert",
    "danger",
    "avoid",
    "evacuate",
    "shelter",
    "secure",
    "emergency",
    "prepare",
)
_REASSURING_TERMS = re.compile(
    r"\b(no significant risk|safe to proceed|conditions are safe|no danger|nothing to worry about|normal conditions)\b",
    re.IGNORECASE,
)
_UNSUPPORTED_ALERT_TERMS = re.compile(
    r"\b(severe weather|extreme weather|dangerous wind|heavy rainfall|heatwave|heat wave|flood warning|red alert|emergency warning)\b",
    re.IGNORECASE,
)


def _deterministic_warning(triggered: list[tuple[RiskRule, float]]) -> str:
    lines = [
        "DETERMINISTIC SAFETY WARNING",
        "The validated SQL weather observations indicate hazardous conditions:",
    ]
    for rule, value in triggered:
        lines.append(
            f"- {rule.hazard_type.replace('_', ' ').title()}: {value:g} {rule.unit} "
            f"(threshold: {rule.threshold:g} {rule.unit})."
        )
        recommendations = sorted({item for items in rule.recommendations.values() for item in items})
        lines.extend(f"  Action: {recommendation}" for recommendation in recommendations)
    lines.append("Follow the latest official IMD advisory and local emergency instructions.")
    return "\n".join(lines)


def _contains_hazard_advisory(response: str, rule: RiskRule) -> bool:
    terms = _HAZARD_TERMS.get(rule.hazard_type, (rule.hazard_type.replace("_", " "),))
    has_hazard = any(term in response.lower() for term in terms)
    has_advice = any(term in response.lower() for term in _ADVISORY_TERMS)
    return has_hazard and has_advice


def apply_safety_guardrails(llm_response: str, numerical_data: dict) -> str:
    """Return only an LLM response that agrees with deterministic hazard rules."""
    try:
        response = llm_response.strip() if isinstance(llm_response, str) else ""
        parameters = {
            str(key): value
            for key, value in numerical_data.items()
            if isinstance(key, str)
        }
        triggered = triggered_rules(parameters)

        if triggered:
            missing_advisories = [
                rule.hazard_type
                for rule, _ in triggered
                if not _contains_hazard_advisory(response, rule)
            ]
            if missing_advisories or _REASSURING_TERMS.search(response):
                logger.warning(
                    "Overriding unsafe LLM response for deterministic hazards: %s",
                    ", ".join(missing_advisories) or "contradictory reassurance",
                )
                return _deterministic_warning(triggered)
            return response

        if _UNSUPPORTED_ALERT_TERMS.search(response):
            logger.warning("Overriding unsupported severe-weather claim from LLM response")
            return (
                "DETERMINISTIC SAFETY NOTICE: The SQL weather observations do not confirm "
                "the severe-weather alert stated in the generated response. No severe alert "
                "is issued by this system from the available observations. Check the latest "
                "official IMD advisory for confirmation."
            )
        return response
    except Exception:
        logger.exception("Safety guardrail evaluation failed closed")
        return SAFETY_CHECK_FAILED_MESSAGE


def _missing_key_message(provider: str) -> str:
    return (
        f"WeatherGPT is configured for {provider}, but its API key is missing. "
        "Set GEMINI_API_KEY or LLM_API_KEY before asking for generated advice."
    )


def placeholder_llm(system_prompt: str, user_query: str) -> str:
    """Safe deterministic fallback when external LLM is not configured or in testing."""
    return (
        "WeatherGPT Advisory: Active conditions have been evaluated against official weather standards. "
        "Adhere to official regional bulletins and stay alert to any changing weather warnings."
    )


def gemini_llm(system_prompt: str, user_query: str) -> str:
    from ..services.metrics import LLM_LATENCY_SECONDS, LLM_REQUESTS_TOTAL
    import time
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return _missing_key_message("Gemini")
    start = time.time()
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"{system_prompt}\n\nUser query: {user_query}")
        text = getattr(response, "text", "")
        LLM_REQUESTS_TOTAL.labels(provider="gemini", status="success").inc()
        LLM_LATENCY_SECONDS.labels(provider="gemini").observe(time.time() - start)
        return text.strip() if text else LLM_ERROR_MESSAGE
    except Exception:
        LLM_REQUESTS_TOTAL.labels(provider="gemini", status="error").inc()
        LLM_LATENCY_SECONDS.labels(provider="gemini").observe(time.time() - start)
        logger.exception("Gemini LLM request failed")
        return LLM_ERROR_MESSAGE


def openai_llm(system_prompt: str, user_query: str) -> str:
    from ..services.metrics import LLM_LATENCY_SECONDS, LLM_REQUESTS_TOTAL
    import time
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return _missing_key_message("OpenAI")
    start = time.time()
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
        )
        text = response.choices[0].message.content or ""
        LLM_REQUESTS_TOTAL.labels(provider="openai", status="success").inc()
        LLM_LATENCY_SECONDS.labels(provider="openai").observe(time.time() - start)
        return text.strip() if text else LLM_ERROR_MESSAGE
    except Exception:
        LLM_REQUESTS_TOTAL.labels(provider="openai", status="error").inc()
        LLM_LATENCY_SECONDS.labels(provider="openai").observe(time.time() - start)
        logger.exception("OpenAI LLM request failed")
        return LLM_ERROR_MESSAGE


class WeatherOrchestrator:
    def __init__(
        self,
        vector_store: VectorStoreManager | None = None,
        llm_client: LLMCallable | None = None,
    ) -> None:
        self.vector_store = vector_store or VectorStoreManager()
        self.llm_client = llm_client or placeholder_llm

    def _weather_data(self, db: Session, latitude: float, longitude: float) -> list[dict[str, Any]]:
        from ..services.credibility import fusion_engine
        now = datetime.now(timezone.utc)
        latitude_delta = func.abs(WeatherObservation.latitude - latitude)
        longitude_delta = func.abs(WeatherObservation.longitude - longitude)
        rows = (
            db.query(WeatherObservation)
            .order_by((latitude_delta + longitude_delta).asc())
            .limit(100)
            .all()
        )
        # Apply multi-source credibility fusion and conflict ranking
        ranked = fusion_engine.resolve_conflicts(rows, db) if rows else []
        return [
            {
                "source": item.observation.source,
                "station_id": item.observation.station_id,
                "latitude": item.observation.latitude,
                "longitude": item.observation.longitude,
                "timestamp": item.observation.timestamp.isoformat(),
                "parameters": item.observation.parameters,
                "credibility_score": item.fused_score.final_score,
                "has_conflict": item.has_conflict,
                "conflict_notes": item.conflict_notes,
            }
            for item in ranked
        ]

    def build_prompt(self, db: Session, user_query: str, latitude: float, longitude: float) -> str:
        weather_data = self._weather_data(db, latitude, longitude)
        return self._render_prompt(weather_data, user_query)

    def _render_prompt(self, weather_data: list[dict[str, Any]], user_query: str) -> str:
        try:
            contexts = self.vector_store.similarity_search(user_query, k=3)
            retrieved_context = "\n\n".join(contexts) if contexts else "No matching official advisory bulletin was found."
        except Exception as exc:
            logger.exception("Advisory retrieval failed")
            retrieved_context = f"No advisory context is available: {exc}"
        return SYSTEM_PROMPT_TEMPLATE.format(
            weather_data=weather_data,
            retrieved_context=retrieved_context,
        )

    def answer(self, db: Session, user_query: str, latitude: float, longitude: float) -> str:
        try:
            weather_data = self._weather_data(db, latitude, longitude)
            system_prompt = self._render_prompt(weather_data, user_query)
            raw_response = self.llm_client(system_prompt, user_query)
            numerical_data = {
                key: max(
                    (
                        record.get("parameters", {}).get(key)
                        for record in weather_data
                        if isinstance(record.get("parameters", {}).get(key), (int, float))
                    ),
                    default=None,
                )
                for key in {
                    key
                    for record in weather_data
                    for key in record.get("parameters", {})
                }
            }
            return apply_safety_guardrails(raw_response, numerical_data)
        except Exception:
            logger.exception("Weather answer generation failed closed")
            return SAFETY_CHECK_FAILED_MESSAGE


def create_orchestrator() -> WeatherOrchestrator:
    """Build an orchestrator using Gemini, OpenAI, or placeholder/mock fallback."""
    provider = os.getenv("LLM_PROVIDER", os.getenv("WEATHERGPT_LLM_PROVIDER", "gemini")).lower()
    if provider == "gemini":
        return WeatherOrchestrator(llm_client=gemini_llm)
    if provider == "openai":
        return WeatherOrchestrator(llm_client=openai_llm)
    if provider in {"mock", "placeholder", "deterministic"}:
        return WeatherOrchestrator(llm_client=placeholder_llm)
    logger.warning("Unknown LLM provider '%s', defaulting to deterministic fallback", provider)
    return WeatherOrchestrator(llm_client=placeholder_llm)
