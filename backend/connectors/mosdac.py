from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

# Key coastal and cyclone-vulnerable observation points covered by INSAT-3D/3DR
DEFAULT_MOSDAC_GRIDS = [
    {"grid_id": "INSAT3D-BOB-01", "name": "Bay of Bengal Central", "lat": 16.5, "lon": 86.0},
    {"grid_id": "INSAT3D-AS-01", "name": "Arabian Sea Central", "lat": 17.0, "lon": 69.0},
    {"grid_id": "INSAT3D-ODISHA", "name": "Odisha Coastal Buffer", "lat": 20.0, "lon": 86.5},
    {"grid_id": "INSAT3D-GUJ", "name": "Gujarat Coastal Buffer", "lat": 22.0, "lon": 69.5},
    {"grid_id": "INSAT3D-TN", "name": "Tamil Nadu Coastal Buffer", "lat": 11.5, "lon": 80.5},
    {"grid_id": "INSAT3D-KERALA", "name": "Kerala Coastal Buffer", "lat": 9.8, "lon": 76.0},
]


class MOSDACConnector(BaseConnector):
    """ISRO MOSDAC (INSAT-3D/3DR) Satellite Data Connector.
    
    Fetches Hydro-Estimator rainfall products, INSAT satellite cloud cover,
    and Sea Surface Temperature (SST) estimates.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            name="MOSDAC",
            source_name="ISRO-MOSDAC",
            timeout_seconds=timeout_seconds,
        )
        self.base_url = base_url or os.getenv("MOSDAC_BASE_URL", "https://www.mosdac.gov.in/api")
        self.api_key = api_key or os.getenv("MOSDAC_API_KEY", "")
        self.product_ids = os.getenv("MOSDAC_PRODUCT_IDS", "3D_L2B_HEM,3D_L2B_IMG").split(",")

    def parse_satellite_payload(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse raw JSON response from MOSDAC catalog/product service."""
        records: list[dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        items = data.get("products", data.get("features", data.get("records", [])))

        for item in items:
            props = item.get("properties", item)
            lat = props.get("latitude") or props.get("lat")
            lon = props.get("longitude") or props.get("lon")
            if lat is None or lon is None:
                continue

            params: dict[str, Any] = {}
            if "rain_rate" in props:
                params["rainfall"] = float(props["rain_rate"])
            elif "rainfall" in props:
                params["rainfall"] = float(props["rainfall"])

            if "cloud_fraction" in props:
                params["cloud_cover"] = float(props["cloud_fraction"]) * 100.0
            elif "cloud_cover" in props:
                params["cloud_cover"] = float(props["cloud_cover"])

            if "sst" in props:
                params["sea_surface_temp"] = float(props["sst"])
            if "brightness_temp" in props:
                params["brightness_temp"] = float(props["brightness_temp"])

            if params:
                records.append(
                    self.normalize_record(
                        station_id=props.get("grid_id", f"MOSDAC-{len(records)+1}"),
                        latitude=float(lat),
                        longitude=float(lon),
                        timestamp=props.get("observation_time", now_iso),
                        parameters=params,
                    )
                )
        return records

    async def fetch(self) -> list[dict[str, Any]]:
        """Query MOSDAC API or synthesize satellite telemetry when offline."""
        client = await self.get_client()
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/catalog/latest"
        try:
            logger.info("[LIVE DATA] Querying ISRO MOSDAC endpoint %s", url)
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                parsed = self.parse_satellite_payload(response.json())
                if parsed:
                    logger.info("[LIVE DATA] Fetched %d real INSAT satellite observations from MOSDAC", len(parsed))
                    return parsed
        except Exception as exc:
            logger.warning("[LIVE DATA] MOSDAC live query failed (%s); degrading to synthetic satellite swath", exc)

        logger.warning("[FALLBACK/SYNTHETIC DATA] Generating synthetic satellite swath telemetry for %d coastal/oceanic nodes", len(DEFAULT_MOSDAC_GRIDS))
        return self._generate_swath_telemetry()

    def _generate_swath_telemetry(self) -> list[dict[str, Any]]:
        """Fallback satellite swath telemetry for high-risk coastal oceanic grids."""
        import random
        now = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []

        for grid in DEFAULT_MOSDAC_GRIDS:
            records.append(
                self.normalize_record(
                    station_id=grid["grid_id"],
                    latitude=grid["lat"],
                    longitude=grid["lon"],
                    timestamp=now,
                    parameters={
                        "rainfall": round(max(0.0, random.uniform(-2, 35)), 1),
                        "cloud_cover": round(random.uniform(40, 95), 1),
                        "brightness_temp": round(random.uniform(220, 280), 1),
                        "humidity": round(random.uniform(70, 95), 1),
                    },
                    is_synthetic=True,
                )
            )
        return records
