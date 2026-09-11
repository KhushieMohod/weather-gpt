from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

# Sample major IMD AWS stations across India for fallback / location mapping
DEFAULT_IMD_STATIONS = {
    "DELHI_SAF": {"lat": 28.585, "lon": 77.206, "name": "Delhi Safdarjung"},
    "MUMBAI_SCL": {"lat": 19.117, "lon": 72.856, "name": "Mumbai Santacruz"},
    "CHENNAI_MNB": {"lat": 12.994, "lon": 80.180, "name": "Chennai Meenambakkam"},
    "KOLKATA_ALIP": {"lat": 22.533, "lon": 88.324, "name": "Kolkata Alipore"},
    "BENGALURU_HAL": {"lat": 12.953, "lon": 77.668, "name": "Bengaluru HAL"},
    "HYDERABAD_BEG": {"lat": 17.453, "lon": 78.467, "name": "Hyderabad Begumpet"},
    "BHUBANESWAR": {"lat": 20.259, "lon": 85.818, "name": "Bhubaneswar Airport"},
    "AHMEDABAD": {"lat": 23.073, "lon": 72.634, "name": "Ahmedabad Airport"},
    "GUWAHATI": {"lat": 26.106, "lon": 91.585, "name": "Guwahati Borjhar"},
}


class IMDConnector(BaseConnector):
    """India Meteorological Department (IMD) AWS & Bulletin Connector.
    
    Fetches real-time observations and district forecasts from IMD's public endpoints.
    """

    def __init__(
        self,
        base_url: str | None = None,
        forecast_url: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(
            name="IMD",
            source_name="IMD",
            timeout_seconds=float(os.getenv("IMD_TIMEOUT_SECONDS", str(timeout_seconds))),
        )
        self.base_url = base_url or os.getenv("IMD_BASE_URL", "https://mausam.imd.gov.in/api")
        self.forecast_url = forecast_url or os.getenv(
            "IMD_FORECAST_URL",
            "https://internal.imd.gov.in/section/nhac/dynamic/allindia.json",
        )

    def parse_station_payload(self, data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse raw JSON/dictionary records from IMD station observation endpoints."""
        records: list[dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        items = data if isinstance(data, list) else data.get("stations", data.get("data", [data]))
        for item in items:
            station_id = item.get("station_id") or item.get("StationId") or item.get("id") or item.get("station_name")
            lat = item.get("latitude") or item.get("lat") or item.get("Latitude")
            lon = item.get("longitude") or item.get("lon") or item.get("Longitude")
            
            # If coordinates are missing, attempt lookup from station lookup table
            if (lat is None or lon is None) and station_id in DEFAULT_IMD_STATIONS:
                lat = DEFAULT_IMD_STATIONS[station_id]["lat"]
                lon = DEFAULT_IMD_STATIONS[station_id]["lon"]

            if lat is None or lon is None:
                continue

            # Extract weather parameters
            params: dict[str, Any] = {}
            temp = item.get("temperature") or item.get("temp") or item.get("TEMP")
            if temp is not None:
                try:
                    params["temperature"] = float(temp)
                except (ValueError, TypeError):
                    pass

            humidity = item.get("humidity") or item.get("rh") or item.get("RH")
            if humidity is not None:
                try:
                    params["humidity"] = float(humidity)
                except (ValueError, TypeError):
                    pass

            rainfall = item.get("rainfall") or item.get("rain") or item.get("RAIN_FALL") or item.get("rain_24h")
            if rainfall is not None:
                try:
                    params["rainfall"] = max(0.0, float(rainfall))
                except (ValueError, TypeError):
                    pass

            wind_speed = item.get("wind_speed") or item.get("wind") or item.get("WIND_SPEED")
            if wind_speed is not None:
                try:
                    params["wind_speed"] = max(0.0, float(wind_speed))
                except (ValueError, TypeError):
                    pass

            pressure = item.get("pressure") or item.get("mslp") or item.get("PRESSURE")
            if pressure is not None:
                try:
                    params["pressure"] = float(pressure)
                except (ValueError, TypeError):
                    pass

            ts = item.get("timestamp") or item.get("dateTime") or item.get("date_time") or now_iso

            if params:
                records.append(
                    self.normalize_record(
                        station_id=str(station_id) if station_id else "IMD-UNKNOWN",
                        latitude=float(lat),
                        longitude=float(lon),
                        timestamp=ts,
                        parameters=params,
                    )
                )
        return records

    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch observations from IMD API or endpoints with graceful degradation."""
        client = await self.get_client()
        endpoints = [
            f"{self.base_url}/current_weather",
            self.forecast_url,
        ]

        for url in endpoints:
            try:
                logger.info("Fetching IMD observations from %s", url)
                response = await client.get(url)
                if response.status_code == 200:
                    payload = response.json()
                    parsed = self.parse_station_payload(payload)
                    if parsed:
                        logger.info("[LIVE DATA] Successfully parsed %d real observations from IMD", len(parsed))
                        return parsed
            except httpx.HTTPError as exc:
                logger.warning("[LIVE DATA] IMD fetch error from %s: %s", url, str(exc))
            except Exception as exc:
                logger.warning("[LIVE DATA] Unexpected error parsing IMD from %s: %s", url, str(exc))

        logger.warning("[FALLBACK/SYNTHETIC DATA] IMD external endpoints unreachable or returned no data; generating synthetic telemetry from %d known IMD stations", len(DEFAULT_IMD_STATIONS))
        return self._generate_telemetry_records()

    def _generate_telemetry_records(self) -> list[dict[str, Any]]:
        """Telemetry fallback keeping station coordinates realistic to maintain system operation."""
        import random
        now = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []
        for station_id, meta in DEFAULT_IMD_STATIONS.items():
            records.append(
                self.normalize_record(
                    station_id=station_id,
                    latitude=meta["lat"],
                    longitude=meta["lon"],
                    timestamp=now,
                    parameters={
                        "temperature": round(26.0 + random.uniform(-4, 8), 1),
                        "humidity": round(65.0 + random.uniform(-15, 25), 1),
                        "rainfall": round(max(0.0, random.uniform(-5, 30)), 1),
                        "wind_speed": round(14.0 + random.uniform(-5, 25), 1),
                        "pressure": round(1010.0 + random.uniform(-6, 6), 1),
                    },
                    is_synthetic=True,
                )
            )
        return records
