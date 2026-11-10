"""Weather risk classification.

The thresholds and load rules from the brief are expressed as data so they read
like the spec and can be changed in one place. See docs/ARCHITECTURE.md §2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    """Ordered risk levels; the integer value doubles as the risk score."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def slug(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Threshold:
    """A value at which ``level`` starts. ``inclusive`` means ``>=``; otherwise ``>``."""

    level: RiskLevel
    value: float
    inclusive: bool = True

    def is_met(self, measurement: float) -> bool:
        return measurement >= self.value if self.inclusive else measurement > self.value


# Ascending order. Bands include their lower bound; the brief states the rain and
# snow No Travel limits as strictly greater-than.
WIND_MPH_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold(RiskLevel.MODERATE, 25),
    Threshold(RiskLevel.HIGH, 35),
    Threshold(RiskLevel.SEVERE, 45),
    Threshold(RiskLevel.NO_TRAVEL, 55),
)
RAIN_IN_HR_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold(RiskLevel.MODERATE, 0.10),
    Threshold(RiskLevel.HIGH, 0.25),
    Threshold(RiskLevel.SEVERE, 0.50),
    Threshold(RiskLevel.NO_TRAVEL, 1.00, inclusive=False),
)
SNOW_IN_HR_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold(RiskLevel.MODERATE, 0.5),
    Threshold(RiskLevel.HIGH, 1.0),
    Threshold(RiskLevel.SEVERE, 2.0),
    Threshold(RiskLevel.NO_TRAVEL, 3.0, inclusive=False),
)


@dataclass(frozen=True, slots=True)
class LoadRule:
    """Escalates the wind level for heavy loads: ``min_wind <= wind < max_wind`` and
    ``load > min_load`` raises the level to ``level``."""

    min_wind_mph: float
    max_wind_mph: float
    min_load_lb: float
    level: RiskLevel

    def applies(self, wind_mph: float, load_lb: float) -> bool:
        return self.min_wind_mph <= wind_mph < self.max_wind_mph and load_lb > self.min_load_lb


# ">= 55 mph → No Travel for any load" is already enforced by the wind thresholds.
LOAD_RULES: tuple[LoadRule, ...] = (
    LoadRule(45, 55, 30_000, RiskLevel.NO_TRAVEL),
    LoadRule(35, 45, 40_000, RiskLevel.SEVERE),
)


@dataclass(frozen=True, slots=True)
class WeatherConditions:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class FactorLevels:
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    load_escalated: bool

    @property
    def overall(self) -> RiskLevel:
        return max(self.wind, self.rain, self.snow)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    wind_level: RiskLevel
    rain_level: RiskLevel
    snow_level: RiskLevel
    reasons: tuple[str, ...]


def classify(measurement: float, thresholds: Sequence[Threshold]) -> RiskLevel:
    level = RiskLevel.LOW
    for threshold in thresholds:
        if threshold.is_met(measurement):
            level = threshold.level
    return level


def wind_level_for_load(wind_mph: float, load_lb: float) -> tuple[RiskLevel, bool]:
    """Wind level after load rules; also returns whether a load rule raised it."""
    base = classify(wind_mph, WIND_MPH_THRESHOLDS)
    escalated = max(
        (rule.level for rule in LOAD_RULES if rule.applies(wind_mph, load_lb)),
        default=RiskLevel.LOW,
    )
    return (escalated, True) if escalated > base else (base, False)


def factor_levels(conditions: WeatherConditions, load_lb: float) -> FactorLevels:
    wind, escalated = wind_level_for_load(conditions.wind_mph, load_lb)
    return FactorLevels(
        wind=wind,
        rain=classify(conditions.rain_in_hr, RAIN_IN_HR_THRESHOLDS),
        snow=classify(conditions.snow_in_hr, SNOW_IN_HR_THRESHOLDS),
        load_escalated=escalated,
    )


def assess(conditions: WeatherConditions, load_lb: float) -> RiskAssessment:
    """Classify a checkpoint and explain which factors drive the result."""
    levels = factor_levels(conditions, load_lb)
    reasons: list[str] = []
    if levels.wind > RiskLevel.LOW:
        load_note = f" with {load_lb:,.0f} lb load" if levels.load_escalated else ""
        reasons.append(f"Wind {conditions.wind_mph:.0f} mph{load_note}: {levels.wind.label}")
    if levels.rain > RiskLevel.LOW:
        reasons.append(f"Rain {conditions.rain_in_hr:.2f} in/hr: {levels.rain.label}")
    if levels.snow > RiskLevel.LOW:
        reasons.append(f"Snow {conditions.snow_in_hr:.2f} in/hr: {levels.snow.label}")

    return RiskAssessment(
        level=levels.overall,
        wind_level=levels.wind,
        rain_level=levels.rain,
        snow_level=levels.snow,
        reasons=tuple(reasons),
    )
