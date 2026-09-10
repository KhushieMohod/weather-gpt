from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

SUPPORTED_SOURCES = ("IMD", "ISRO-MOSDAC", "GFS/WRF", "ERA5")


def generate_mock_weather_stream(
    count: int = 4,
    *,
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate representative records for each supported weather source."""
    if count < 1:
        raise ValueError("count must be at least 1")

    generator = random.Random(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    records: list[dict[str, Any]] = []

    for index in range(count):
        source = SUPPORTED_SOURCES[index % len(SUPPORTED_SOURCES)]
        timestamp = now - timedelta(minutes=index * 15)
        common = {
            "source": source,
            "station_id": f"MOCK-{index + 1:03d}",
            "latitude": round(latitude + generator.uniform(-0.02, 0.02), 5),
            "longitude": round(longitude + generator.uniform(-0.02, 0.02), 5),
            "timestamp": timestamp.isoformat(),
        }

        if source == "IMD":
            parameters = {
                "temperature": round(generator.uniform(18, 42), 2),
                "rainfall": round(generator.uniform(0, 30), 2),
                "wind_speed": round(generator.uniform(0, 35), 2),
                "wind_direction": generator.randint(0, 359),
            }
        elif source == "ISRO-MOSDAC":
            parameters = {
                "humidity": round(generator.uniform(25, 95), 2),
                "cloud_cover": round(generator.uniform(0, 100), 2),
                "pressure": round(generator.uniform(985, 1030), 2),
            }
        elif source == "GFS/WRF":
            parameters = {
                "forecast_temperature": round(generator.uniform(18, 42), 2),
                "forecast_rainfall": round(generator.uniform(0, 50), 2),
                "forecast_wind_speed": round(generator.uniform(0, 45), 2),
                "forecast_horizon_hours": 24,
            }
        else:
            parameters = {
                "historical_temperature": round(generator.uniform(18, 40), 2),
                "historical_rainfall": round(generator.uniform(0, 40), 2),
                "historical_humidity": round(generator.uniform(25, 95), 2),
                "reference_period": "1991-2020",
            }

        records.append({**common, "parameters": parameters})

    return records


def generate_mock_weather_stream_json(count: int = 4, seed: int | None = None) -> str:
    """Return the mock stream as a JSON array suitable for ingestion tests."""
    return json.dumps(generate_mock_weather_stream(count, seed=seed), default=str)
