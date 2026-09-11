from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

# Representative regional forecast nodes across India meteorological zones
GFS_INDIA_ZONES = [
    {"zone_id": "GFS-NORTH-PLN", "lat": 28.5, "lon": 77.0, "name": "Northern Plains"},
    {"zone_id": "GFS-CENTRAL-DECCAN", "lat": 21.0, "lon": 79.0, "name": "Central Deccan"},
    {"zone_id": "GFS-WEST-COAST", "lat": 15.5, "lon": 73.8, "name": "Konkan/Goa Coast"},
    {"zone_id": "GFS-EAST-COAST", "lat": 17.7, "lon": 83.3, "name": "Andhra/Odisha Coast"},
    {"zone_id": "GFS-SOUTH-PEN", "lat": 10.0, "lon": 77.5, "name": "Southern Peninsula"},
    {"zone_id": "GFS-NORTHEAST", "lat": 25.5, "lon": 91.9, "name": "North East Hills"},
    {"zone_id": "GFS-THAR-DESERT", "lat": 26.9, "lon": 70.9, "name": "Thar Desert Zone"},
]


class GFSConnector(BaseConnector):
    """NOAA Global Forecast System (GFS) & WRF Regional Model Connector.
    
    Accesses NOAA NOMADS HTTP filters and Open-Meteo GFS seamless feeds
    for forecast atmospheric parameters over India.
    """

    def __init__(
        self,
        nomads_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            name="GFS",
            source_name="GFS/WRF",
            timeout_seconds=timeout_seconds,
        )
        self.nomads_url = nomads_url or os.getenv(
            "GFS_NOMADS_URL",
            "https://api.open-meteo.com/v1/gfs",
        )

    def parse_gfs_api_response(
        self,
        data: dict[str, Any],
        station_id: str,
        lat: float,
        lon: float,
    ) -> dict[str, Any] | None:
        """Parse GFS standard timeseries/grid JSON response."""
        hourly = data.get("hourly")
        current = data.get("current")

        params: dict[str, Any] = {}
        ts_str = datetime.now(timezone.utc).isoformat()

        if current and isinstance(current, dict):
            if "temperature_2m" in current:
                params["temperature"] = float(current["temperature_2m"])
            if "relative_humidity_2m" in current:
                params["humidity"] = float(current["relative_humidity_2m"])
            if "precipitation" in current:
                params["rainfall"] = float(current["precipitation"])
            if "wind_speed_10m" in current:
                params["wind_speed"] = float(current["wind_speed_10m"])
            if "surface_pressure" in current:
                params["pressure"] = float(current["surface_pressure"])
            if "time" in current:
                ts_str = current["time"]

        elif hourly and isinstance(hourly, dict):
            times = hourly.get("time", [])
            if times:
                idx = 0  # current / earliest step
                if "temperature_2m" in hourly and hourly["temperature_2m"]:
                    params["temperature"] = float(hourly["temperature_2m"][idx])
                if "relative_humidity_2m" in hourly and hourly["relative_humidity_2m"]:
                    params["humidity"] = float(hourly["relative_humidity_2m"][idx])
                if "precipitation" in hourly and hourly["precipitation"]:
                    params["rainfall"] = float(hourly["precipitation"][idx])
                if "wind_speed_10m" in hourly and hourly["wind_speed_10m"]:
                    params["wind_speed"] = float(hourly["wind_speed_10m"][idx])
                if "surface_pressure" in hourly and hourly["surface_pressure"]:
                    params["pressure"] = float(hourly["surface_pressure"][idx])
                ts_str = times[idx]

        if params:
            return self.normalize_record(
                station_id=station_id,
                latitude=lat,
                longitude=lon,
                timestamp=ts_str,
                parameters=params,
            )
        return None

    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch numerical model runs for key meteorological zones."""
        client = await self.get_client()
        records: list[dict[str, Any]] = []

        for zone in GFS_INDIA_ZONES:
            lat = zone["lat"]
            lon = zone["lon"]
            url = (
                f"{self.nomads_url}?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,surface_pressure"
                f"&forecast_days=1"
            )
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    parsed = self.parse_gfs_api_response(resp.json(), zone["zone_id"], lat, lon)
                    if parsed:
                        records.append(parsed)
            except Exception as exc:
                logger.debug("GFS live query for zone %s failed (%s)", zone["zone_id"], exc)

        if records:
            logger.info("[LIVE DATA] Retrieved %d live GFS numerical model atmospheric nodes", len(records))
            return records

        logger.warning("[FALLBACK/SYNTHETIC DATA] GFS external endpoint unavailable; generating fallback synthetic numerical model telemetry for %d zones", len(GFS_INDIA_ZONES))
        return self._generate_model_telemetry()

    def _generate_model_telemetry(self) -> list[dict[str, Any]]:
        """Fallback simulation maintaining GFS numerical model characteristics."""
        import random
        now = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []
        for zone in GFS_INDIA_ZONES:
            records.append(
                self.normalize_record(
                    station_id=zone["zone_id"],
                    latitude=zone["lat"],
                    longitude=zone["lon"],
                    timestamp=now,
                    parameters={
                        "temperature": round(29.0 + random.uniform(-6, 6), 1),
                        "humidity": round(58.0 + random.uniform(-15, 20), 1),
                        "rainfall": round(max(0.0, random.uniform(-3, 18)), 1),
                        "wind_speed": round(18.0 + random.uniform(-6, 20), 1),
                        "pressure": round(1008.0 + random.uniform(-5, 5), 1),
                    },
                    is_synthetic=True,
                )
            )
        return records
