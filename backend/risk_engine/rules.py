from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskRule:
    hazard_type: str
    parameter_names: tuple[str, ...]
    threshold: float
    severity: str
    unit: str
    audiences: tuple[str, ...]
    recommendations: dict[str, list[str]]


RISK_RULES = (
    RiskRule(
        "heavy_rainfall", ("rainfall", "forecast_rainfall"), 50.0, "high", "mm",
        ("agricultural_workers", "urban_disaster_teams"),
        {
            "agricultural_workers": ["Clear field drains and move livestock to higher ground."],
            "urban_disaster_teams": ["Open flood relief centers and inspect drainage chokepoints."],
        },
    ),
    RiskRule(
        "extreme_heat", ("temperature", "forecast_temperature"), 45.0, "high", "C",
        ("agricultural_workers", "urban_disaster_teams"),
        {
            "agricultural_workers": ["Pause strenuous field work during peak heat and provide water and shade."],
            "urban_disaster_teams": ["Open cooling centers and check on heat-vulnerable residents."],
        },
    ),
    RiskRule(
        "dangerous_wind", ("wind_speed", "forecast_wind_speed"), 60.0, "high", "km/h",
        ("agricultural_workers", "urban_disaster_teams"),
        {
            "agricultural_workers": ["Secure equipment, shelter workers, and protect nursery structures."],
            "urban_disaster_teams": ["Inspect loose signage and prepare emergency crews for fallen infrastructure."],
        },
    ),
    RiskRule(
        "cyclone_warning", ("wind_speed", "forecast_wind_speed"), 90.0, "critical", "km/h",
        ("agricultural_workers", "urban_disaster_teams", "marine_operators"),
        {
            "agricultural_workers": ["Secure equipment, shelter workers, and follow official evacuation instructions."],
            "urban_disaster_teams": ["Activate cyclone response plans and prepare emergency shelters."],
            "marine_operators": ["Keep vessels in safe harbor and follow Coast Guard and port control directions."],
        },
    ),
    RiskRule(
        "flooding_risk", ("rainfall", "forecast_rainfall"), 100.0, "critical", "mm",
        ("agricultural_workers", "urban_disaster_teams"),
        {
            "agricultural_workers": ["Evacuate exposed low-lying fields and move livestock and machinery."],
            "urban_disaster_teams": ["Activate flood response plans and deploy teams to low-lying areas."],
        },
    ),
)


def triggered_rules(parameters: dict[str, Any]) -> list[tuple[RiskRule, float]]:
    triggered: list[tuple[RiskRule, float]] = []
    for rule in RISK_RULES:
        values = [parameters[name] for name in rule.parameter_names if isinstance(parameters.get(name), (int, float))]
        if values:
            value = max(float(item) for item in values)
            if value >= rule.threshold:
                triggered.append((rule, value))
    return triggered