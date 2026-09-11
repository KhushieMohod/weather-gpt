from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from ..models import CredibilityLog, WeatherObservation

logger = logging.getLogger(__name__)

SOURCE_REPUTATION = {
    "IMD": 0.95,
    "ISRO-MOSDAC": 0.95,
    "GFS/WRF": 0.82,
    "ERA5": 0.88,
}


@dataclass(frozen=True)
class ValidationResult:
    normalized: dict[str, Any] | None
    status: str
    score: float
    errors: list[str]
    fused_score: Any | None = None


def _as_number(value: Any, field_name: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        errors.append(f"{field_name} must be a finite number")
        return None
    return float(value)


def _parse_timestamp(value: Any, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append("timestamp must be an ISO-8601 string")
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append("timestamp must be a valid ISO-8601 value")
        return None
    return (timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _quality_errors(parameters: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    numeric_parameters = {key: value for key, value in parameters.items() if isinstance(value, (int, float))}

    for key, value in numeric_parameters.items():
        if not math.isfinite(float(value)):
            errors.append(f"{key} must be finite")

    temperature_values = [value for key, value in numeric_parameters.items() if "temperature" in key and "forecast" not in key]
    rainfall_values = [value for key, value in numeric_parameters.items() if "rainfall" in key]
    if any(value > 60 for value in temperature_values):
        errors.append("temperature exceeds 60 C")
    if any(value < 0 for value in rainfall_values):
        errors.append("rainfall cannot be negative")
    if any(value < 0 for key, value in numeric_parameters.items() if "wind_speed" in key):
        errors.append("wind_speed cannot be negative")
    if any(value < 0 or value > 100 for key, value in numeric_parameters.items() if key in {"humidity", "cloud_cover"}):
        errors.append("humidity and cloud_cover must be between 0 and 100")
    if any(value <= 0 for key, value in numeric_parameters.items() if key == "pressure"):
        errors.append("pressure must be positive")
    return errors


def _find_duplicate(db: Session, normalized: dict[str, Any]) -> bool:
    timestamp = normalized["timestamp"]
    candidates = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.timestamp >= timestamp - timedelta(seconds=1),
            WeatherObservation.timestamp <= timestamp + timedelta(seconds=1),
        )
        .all()
    )
    latitude = round(normalized["latitude"], 2)
    longitude = round(normalized["longitude"], 2)
    return any(
        round(candidate.latitude, 2) == latitude and round(candidate.longitude, 2) == longitude
        for candidate in candidates
    )


def _consistency_score(db: Session, normalized: dict[str, Any]) -> float:
    timestamp = normalized["timestamp"]
    candidates = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.timestamp >= timestamp - timedelta(hours=1),
            WeatherObservation.timestamp <= timestamp + timedelta(hours=1),
        )
        .all()
    )
    latitude = round(normalized["latitude"], 2)
    longitude = round(normalized["longitude"], 2)
    overlaps: list[float] = []
    for candidate in candidates:
        if round(candidate.latitude, 2) != latitude or round(candidate.longitude, 2) != longitude:
            continue
        for key, value in normalized["parameters"].items():
            other = candidate.parameters.get(key)
            if isinstance(value, (int, float)) and isinstance(other, (int, float)):
                tolerance = max(abs(float(value)) * 0.2, 1.0)
                overlaps.append(1.0 if abs(float(value) - float(other)) <= tolerance else 0.0)
    return sum(overlaps) / len(overlaps) if overlaps else 1.0


def validate_observation(payload: Mapping[str, Any], db: Session) -> ValidationResult:
    errors: list[str] = []
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip():
        errors.append("source is required")
        source = "unknown"
    source = source.strip()

    latitude = _as_number(payload.get("latitude"), "latitude", errors)
    longitude = _as_number(payload.get("longitude"), "longitude", errors)
    if latitude is not None and not -90 <= latitude <= 90:
        errors.append("latitude must be between -90 and 90")
    if longitude is not None and not -180 <= longitude <= 180:
        errors.append("longitude must be between -180 and 180")

    timestamp = _parse_timestamp(payload.get("timestamp"), errors)
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict) or not parameters:
        errors.append("parameters must be a non-empty object")
        parameters = {}
    errors.extend(_quality_errors(parameters))

    normalized = None
    if not errors and latitude is not None and longitude is not None and timestamp is not None:
        normalized = {
            "source": source,
            "station_id": payload.get("station_id"),
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp,
            "parameters": dict(parameters),
        }
        if _find_duplicate(db, normalized):
            errors.append("duplicate observation at the rounded location and timestamp")

    consistency = _consistency_score(db, normalized) if normalized else 1.0
    score = max(0.0, min(1.0, SOURCE_REPUTATION.get(source, 0.60) * consistency * (0.5 if errors else 1.0)))
    status = "valid" if normalized and not errors else "rejected"
    if errors:
        logger.warning("Suspect weather data from %s: %s", source, "; ".join(errors))
    return ValidationResult(normalized, status, round(score, 4), errors)


def add_credibility_log(db: Session, payload: Mapping[str, Any], result: ValidationResult) -> CredibilityLog:
    log = CredibilityLog(
        source=str(payload.get("source", "unknown")),
        validation_status=result.status,
        credibility_score=result.score,
        error_details=result.errors,
    )
    db.add(log)
    return log
