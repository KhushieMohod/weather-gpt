from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from sqlalchemy.orm import Session

from ..models import WeatherObservation

logger = logging.getLogger(__name__)

# Default base reputation weights by source
DEFAULT_SOURCE_AUTHORITY = {
    "IMD": 0.95,
    "ISRO-MOSDAC": 0.95,
    "ERA5": 0.88,
    "GFS/WRF": 0.82,
}

# Observation half-life in hours for exponential decay
SOURCE_HALF_LIFE_HOURS = {
    "IMD": 3.0,
    "ISRO-MOSDAC": 4.0,
    "GFS/WRF": 12.0,
    "ERA5": 72.0,  # reanalysis maintains validity over days
}


@dataclass(frozen=True)
class FusedScore:
    """Detailed breakdown of multi-source credibility calculation."""
    final_score: float
    authority_score: float
    freshness_score: float
    cross_source_score: float
    completeness_score: float
    temporal_consistency_score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RankedObservation:
    """An observation annotated with fused credibility score and conflict flags."""
    observation: WeatherObservation
    fused_score: FusedScore
    has_conflict: bool = False
    conflict_notes: list[str] = field(default_factory=list)


class CredibilityFusionEngine:
    """Multi-source Bayesian credibility fusion engine.
    
    Evaluates weather observations combining:
    1. Source Authority / Reputation
    2. Freshness Exponential Decay
    3. Parameter Completeness
    4. Cross-Source Multi-Sensor Agreement
    5. Temporal Station Consistency
    """

    def __init__(
        self,
        source_authority: Mapping[str, float] | None = None,
        half_life_hours: Mapping[str, float] | None = None,
    ) -> None:
        self.source_authority = dict(source_authority or DEFAULT_SOURCE_AUTHORITY)
        self.half_life_hours = dict(half_life_hours or SOURCE_HALF_LIFE_HOURS)

    def calculate_authority(self, source: str) -> float:
        """Base authority score for source."""
        return self.source_authority.get(source, 0.60)

    def calculate_freshness(self, timestamp: datetime, source: str, now: datetime | None = None) -> float:
        """Exponential freshness decay: e^(-lambda * dt)."""
        if now is None:
            now = datetime.now(timezone.utc)

        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        
        age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
        half_life = self.half_life_hours.get(source, 6.0)
        decay_constant = math.log(2) / max(0.1, half_life)
        
        return math.exp(-decay_constant * age_hours)

    def calculate_completeness(self, parameters: Mapping[str, Any]) -> float:
        """Score based on key parameter presence: temperature, humidity, rainfall, wind_speed, pressure."""
        core_keys = {"temperature", "humidity", "rainfall", "wind_speed", "pressure"}
        present = sum(1 for k in core_keys if k in parameters and parameters[k] is not None)
        return min(1.0, max(0.4, (present / len(core_keys)) * 1.0 + 0.2))

    def calculate_cross_source_agreement(
        self,
        db: Session,
        normalized: Mapping[str, Any],
        spatial_radius_deg: float = 0.5,
        temporal_window_hours: float = 2.0,
    ) -> tuple[float, list[str]]:
        """Evaluate agreement against peer sources in same spatio-temporal radius."""
        ts: datetime = normalized["timestamp"]
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        lat = float(normalized["latitude"])
        lon = float(normalized["longitude"])
        source = normalized.get("source", "")
        params = normalized.get("parameters", {})

        candidates = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.timestamp >= ts_utc - timedelta(hours=temporal_window_hours),
                WeatherObservation.timestamp <= ts_utc + timedelta(hours=temporal_window_hours),
                WeatherObservation.latitude >= lat - spatial_radius_deg,
                WeatherObservation.latitude <= lat + spatial_radius_deg,
                WeatherObservation.longitude >= lon - spatial_radius_deg,
                WeatherObservation.longitude <= lon + spatial_radius_deg,
            )
            .all()
        )

        peer_candidates = [c for c in candidates if c.source != source]
        if not peer_candidates:
            return 1.0, []

        agreements: list[float] = []
        conflicts: list[str] = []

        for peer in peer_candidates:
            peer_params = peer.parameters or {}
            for param_name, current_val in params.items():
                if param_name in peer_params and isinstance(current_val, (int, float)):
                    peer_val = peer_params[param_name]
                    if isinstance(peer_val, (int, float)):
                        diff = abs(float(current_val) - float(peer_val))
                        rel_tolerance = max(abs(float(current_val)) * 0.25, 2.0)
                        if diff <= rel_tolerance:
                            agreements.append(1.0)
                        else:
                            penalty = max(0.0, 1.0 - (diff / (rel_tolerance * 3)))
                            agreements.append(penalty)
                            conflicts.append(
                                f"{param_name} divergence: {source}={current_val} vs {peer.source}={peer_val}"
                            )

        score = sum(agreements) / len(agreements) if agreements else 1.0
        return max(0.2, score), conflicts

    def calculate_temporal_consistency(
        self,
        db: Session,
        normalized: Mapping[str, Any],
    ) -> float:
        """Check if station has unrealistic sudden spikes compared to 3-hour history."""
        station_id = normalized.get("station_id")
        if not station_id:
            return 1.0

        ts: datetime = normalized["timestamp"]
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

        recent = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.station_id == station_id,
                WeatherObservation.timestamp >= ts_utc - timedelta(hours=3),
                WeatherObservation.timestamp < ts_utc,
            )
            .order_by(WeatherObservation.timestamp.desc())
            .first()
        )

        if not recent or not recent.parameters:
            return 1.0

        params = normalized.get("parameters", {})
        temp = params.get("temperature")
        recent_temp = recent.parameters.get("temperature")
        if temp is not None and recent_temp is not None:
            # Temperature changing more than 12°C in <3 hours is physically anomalous
            if abs(float(temp) - float(recent_temp)) > 12.0:
                return 0.5

        return 1.0

    def compute_fused_score(
        self,
        normalized: Mapping[str, Any],
        db: Session,
        has_validation_errors: bool = False,
    ) -> FusedScore:
        """Compute the weighted fused credibility score."""
        source = str(normalized.get("source", "unknown"))
        timestamp = normalized.get("timestamp")
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now(timezone.utc)
        parameters = normalized.get("parameters", {})

        authority = self.calculate_authority(source)
        is_synthetic = parameters.get("data_mode") == "FALLBACK/SYNTHETIC DATA"
        effective_authority = authority * 0.60 if is_synthetic else authority

        freshness = self.calculate_freshness(timestamp, source)
        completeness = self.calculate_completeness(parameters)
        cross_source, conflicts = self.calculate_cross_source_agreement(db, normalized)
        temporal = self.calculate_temporal_consistency(db, normalized)

        # Base weighted fusion
        weights = {
            "authority": 0.40,
            "cross_source": 0.25,
            "freshness": 0.15,
            "temporal": 0.10,
            "completeness": 0.10,
        }

        raw_fused = (
            effective_authority * weights["authority"]
            + cross_source * weights["cross_source"]
            + freshness * weights["freshness"]
            + temporal * weights["temporal"]
            + completeness * weights["completeness"]
        )

        if has_validation_errors:
            raw_fused *= 0.5

        final_score = round(max(0.0, min(1.0, raw_fused)), 4)

        return FusedScore(
            final_score=final_score,
            authority_score=round(effective_authority, 4),
            freshness_score=round(freshness, 4),
            cross_source_score=round(cross_source, 4),
            completeness_score=round(completeness, 4),
            temporal_consistency_score=round(temporal, 4),
            details={
                "conflicts": conflicts,
                "data_mode": "FALLBACK/SYNTHETIC DATA" if is_synthetic else "LIVE DATA",
                "is_synthetic": is_synthetic,
            },
        )

    def resolve_conflicts(
        self,
        observations: Sequence[WeatherObservation],
        db: Session,
    ) -> list[RankedObservation]:
        """Rank multiple observations by credibility and flag conflicting parameters."""
        ranked: list[RankedObservation] = []
        for obs in observations:
            normalized = {
                "source": obs.source,
                "station_id": obs.station_id,
                "latitude": obs.latitude,
                "longitude": obs.longitude,
                "timestamp": obs.timestamp,
                "parameters": obs.parameters or {},
            }
            fused = self.compute_fused_score(normalized, db)
            conflicts = fused.details.get("conflicts", [])
            ranked.append(
                RankedObservation(
                    observation=obs,
                    fused_score=fused,
                    has_conflict=bool(conflicts),
                    conflict_notes=conflicts,
                )
            )

        # Sort descending by credibility score, then recency
        ranked.sort(key=lambda r: (r.fused_score.final_score, r.observation.timestamp), reverse=True)
        return ranked


# Global singleton engine
fusion_engine = CredibilityFusionEngine()
