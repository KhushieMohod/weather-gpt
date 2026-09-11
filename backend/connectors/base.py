from __future__ import annotations

import abc
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

import httpx

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Base exception for data connector failures."""
    def __init__(self, message: str, source: str, is_transient: bool = True):
        super().__init__(message)
        self.source = source
        self.is_transient = is_transient


class BaseConnector(abc.ABC):
    """Abstract Base Class for Weather Data Connectors.
    
    All external connectors (IMD, MOSDAC, GFS, ERA5) must implement this interface.
    """

    def __init__(
        self,
        name: str,
        source_name: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.name = name
        self.source_name = source_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or initialize an async HTTP client."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
                headers={"User-Agent": f"WeatherGPT/{self.name}-Connector/1.0"},
            )
        return self.client

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None

    @abc.abstractmethod
    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch raw data from external source and normalize to WeatherObservation payloads.
        
        Returns:
            list of dicts matching:
            {
                "source": str,
                "station_id": str | None,
                "latitude": float,
                "longitude": float,
                "timestamp": str (ISO-8601),
                "parameters": dict[str, float | int | str]
            }
        """
        raise NotImplementedError

    def normalize_record(
        self,
        station_id: str | None,
        latitude: float,
        longitude: float,
        timestamp: datetime | str,
        parameters: Mapping[str, Any],
        is_synthetic: bool = False,
    ) -> dict[str, Any]:
        """Helper to create a validated standardized observation dictionary."""
        if isinstance(timestamp, datetime):
            ts_str = (
                timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            ).isoformat()
        else:
            ts_str = str(timestamp)

        cleaned_params: dict[str, Any] = {}
        for k, v in parameters.items():
            if v is not None:
                cleaned_params[k] = v

        if "data_mode" not in cleaned_params:
            cleaned_params["data_mode"] = "FALLBACK/SYNTHETIC DATA" if is_synthetic else "LIVE DATA"

        return {
            "source": self.source_name,
            "station_id": station_id,
            "latitude": round(float(latitude), 4),
            "longitude": round(float(longitude), 4),
            "timestamp": ts_str,
            "parameters": cleaned_params,
        }
