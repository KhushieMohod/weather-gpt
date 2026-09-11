from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

ERA5_BASE_LOCATIONS = [
    {"point_id": "ERA5-DELHI", "lat": 28.61, "lon": 77.23},
    {"point_id": "ERA5-MUMBAI", "lat": 19.08, "lon": 72.88},
    {"point_id": "ERA5-CHENNAI", "lat": 13.08, "lon": 80.27},
    {"point_id": "ERA5-KOLKATA", "lat": 22.57, "lon": 88.36},
    {"point_id": "ERA5-HYDERABAD", "lat": 17.38, "lon": 78.48},
    {"point_id": "ERA5-BENGALURU", "lat": 12.97, "lon": 77.59},
]


class ERA5Connector(BaseConnector):
    """ECMWF ERA5 Climate Reanalysis Data Connector.
    
    Interfaces with Copernicus Climate Data Store (CDS API) or open ERA5 reanalysis
    endpoints to establish baseline climatology and cross-source verification.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 40.0,
    ) -> None:
        super().__init__(
            name="ERA5",
            source_name="ERA5",
            timeout_seconds=timeout_seconds,
        )
        self.api_url = api_url or os.getenv("CDS_API_URL", "https://cds.climate.copernicus.eu/api/v2")
        self.api_key = api_key or os.getenv("CDS_API_KEY", "")

    def parse_era5_json(self, data: dict[str, Any], point_id: str, lat: float, lon: float) -> dict[str, Any] | None:
        """Parse normalized ERA5 timeseries response."""
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})
        current = data.get("current", {})

        params: dict[str, Any] = {}
        target_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        if hourly and "time" in hourly and hourly["time"]:
            idx = -1  # latest available
            if "temperature_2m" in hourly and hourly["temperature_2m"]:
                params["temperature"] = float(hourly["temperature_2m"][idx])
            if "relative_humidity_2m" in hourly and hourly["relative_humidity_2m"]:
                params["humidity"] = float(hourly["relative_humidity_2m"][idx])
            if "precipitation" in hourly and hourly["precipitation"]:
                params["rainfall"] = float(hourly["precipitation"][idx])
            if "surface_pressure" in hourly and hourly["surface_pressure"]:
                params["pressure"] = float(hourly["surface_pressure"][idx])
            if "wind_speed_10m" in hourly and hourly["wind_speed_10m"]:
                params["wind_speed"] = float(hourly["wind_speed_10m"][idx])
            target_time = hourly["time"][idx]
        elif current:
            for k in ["temperature_2m", "relative_humidity_2m", "precipitation", "surface_pressure"]:
                if k in current:
                    params[k.replace("_2m", "")] = float(current[k])

        if params:
            return self.normalize_record(
                station_id=point_id,
                latitude=lat,
                longitude=lon,
                timestamp=target_time,
                parameters=params,
            )
        return None

    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch ERA5 reanalysis data via open archive or synthesize from baseline."""
        client = await self.get_client()
        records: list[dict[str, Any]] = []

        # Use Open-Meteo ERA5 historical archive for low-latency retrieval
        archive_base = "https://archive-api.open-meteo.com/v1/era5"
        yesterday = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")

        for loc in ERA5_BASE_LOCATIONS:
            lat = loc["lat"]
            lon = loc["lon"]
            url = (
                f"{archive_base}?latitude={lat}&longitude={lon}"
                f"&start_date={yesterday}&end_date={yesterday}"
                f"&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m"
            )
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    parsed = self.parse_era5_json(resp.json(), loc["point_id"], lat, lon)
                    if parsed:
                        records.append(parsed)
            except Exception as exc:
                logger.debug("ERA5 archive lookup failed for %s (%s)", loc["point_id"], exc)

        if records:
            logger.info("[LIVE DATA] Fetched %d real ERA5 reanalysis records from open archive", len(records))
            return records

        logger.warning("[FALLBACK/SYNTHETIC DATA] ERA5 archive inaccessible; generating synthetic climatological reanalysis baseline for %d locations", len(ERA5_BASE_LOCATIONS))
        return self._generate_climatological_records()

    def _generate_climatological_records(self) -> list[dict[str, Any]]:
        """Fallback baseline matching ERA5 climatology."""
        import random
        # ERA5 typically has ~5 days lag
        obs_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        records: list[dict[str, Any]] = []
        for loc in ERA5_BASE_LOCATIONS:
            records.append(
                self.normalize_record(
                    station_id=loc["point_id"],
                    latitude=loc["lat"],
                    longitude=loc["lon"],
                    timestamp=obs_time,
                    parameters={
                        "temperature": round(27.5 + random.uniform(-4, 5), 1),
                        "humidity": round(68.0 + random.uniform(-10, 15), 1),
                        "rainfall": round(max(0.0, random.uniform(-2, 12)), 1),
                        "pressure": round(1011.0 + random.uniform(-3, 3), 1),
                        "wind_speed": round(12.0 + random.uniform(-4, 8), 1),
                    },
                    is_synthetic=True,
                )
            )
        return records
