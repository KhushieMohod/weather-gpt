from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

from .metrics import LLM_LATENCY_SECONDS, LLM_REQUESTS_TOTAL

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration attributes for LLM providers."""
    provider: str
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: float = 30.0
    max_retries: int = 2
    api_key_configured: bool = False


class LLMProviderRegistry:
    """Registry managing LLM provider callables with metrics and automatic fallback."""

    def __init__(self) -> None:
        self._providers: dict[str, Callable[[str], str]] = {}

    def register(self, name: str, fn: Callable[[str], str]) -> None:
        self._providers[name.lower()] = fn

    def invoke(
        self,
        prompt: str,
        primary_provider: str | None = None,
        fallback_provider: str | None = None,
    ) -> str:
        """Execute inference with latency metrics and failover."""
        primary = (primary_provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
        fallback = (fallback_provider or os.getenv("LLM_FALLBACK_PROVIDER", "openai")).lower()

        chain = [primary]
        if fallback and fallback != primary:
            chain.append(fallback)
        if "mock" not in chain and "deterministic" not in chain:
            chain.append("mock")

        last_error = None
        for provider_name in chain:
            handler = self._providers.get(provider_name)
            if not handler:
                continue

            start_time = time.time()
            try:
                logger.info("Executing LLM generation via provider: %s", provider_name)
                response = handler(prompt)
                latency = time.time() - start_time
                LLM_REQUESTS_TOTAL.labels(provider=provider_name, status="success").inc()
                LLM_LATENCY_SECONDS.labels(provider=provider_name).observe(latency)
                return response
            except Exception as exc:
                latency = time.time() - start_time
                LLM_REQUESTS_TOTAL.labels(provider=provider_name, status="error").inc()
                LLM_LATENCY_SECONDS.labels(provider=provider_name).observe(latency)
                logger.warning("LLM provider %s failed (%s); trying fallback", provider_name, exc)
                last_error = exc

        # Deterministic emergency guidance if all providers fail
        return (
            "WeatherGPT Advisory: Active weather advisory guidelines indicate prioritizing life safety. "
            "Please monitor official local disaster management alerts and stay indoors during extreme conditions."
        )


def validate_llm_environment() -> dict[str, Any]:
    """Inspect environment configuration for LLM keys and health."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    gemini_ready = bool(gemini_key and gemini_key != "your_key_here" and len(gemini_key) > 8)
    openai_ready = bool(openai_key and openai_key != "your_key_here" and len(openai_key) > 8)

    status = {
        "configured_provider": provider,
        "gemini_configured": gemini_ready,
        "openai_configured": openai_ready,
        "active": False,
    }

    if provider == "gemini":
        status["active"] = gemini_ready
    elif provider == "openai":
        status["active"] = openai_ready
    elif provider in {"mock", "deterministic"}:
        status["active"] = True

    if not status["active"]:
        logger.warning(
            "Selected LLM provider '%s' has no valid API key configured in environment. "
            "WeatherGPT will operate with deterministic RAG & fallback safety warnings.",
            provider,
        )
    else:
        logger.info("LLM provider '%s' is configured and verified ready.", provider)

    return status


llm_registry = LLMProviderRegistry()
