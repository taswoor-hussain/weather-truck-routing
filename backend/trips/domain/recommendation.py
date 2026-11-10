"""Per-route risk summaries and route ranking (see docs/ARCHITECTURE.md §2.5–2.6)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from trips.domain.risk import RiskLevel

MILES_PRECISION = 1
RISK_PRECISION = 2


@dataclass(frozen=True, slots=True)
class RouteRiskSummary:
    distance_mi: float
    duration_s: float
    average_risk: float
    miles_by_level: dict[RiskLevel, float] = field(default_factory=dict)

    def miles(self, level: RiskLevel) -> float:
        return self.miles_by_level.get(level, 0.0)

    @property
    def ranking_key(self) -> tuple[float, ...]:
        """Lexicographic preference: lower is better on every component."""
        return (
            round(self.miles(RiskLevel.NO_TRAVEL), MILES_PRECISION),
            round(self.miles(RiskLevel.SEVERE), MILES_PRECISION),
            round(self.miles(RiskLevel.HIGH), MILES_PRECISION),
            round(self.average_risk, RISK_PRECISION),
            self.duration_s,
        )


def summarise_route(
    checkpoint_distances: Sequence[float],
    levels: Sequence[RiskLevel],
    distance_mi: float,
    duration_s: float,
) -> RouteRiskSummary:
    """Attribute route miles to risk levels.

    Each checkpoint covers the stretch of road closest to it (half-way to its
    neighbours), so the mileage per level always sums to the route length. The
    average risk is the distance-weighted mean score over those stretches.
    """
    if len(checkpoint_distances) != len(levels) or not levels:
        raise ValueError("Each checkpoint needs exactly one risk level.")

    miles_by_level: dict[RiskLevel, float] = {}
    weighted_score = 0.0
    last = len(levels) - 1
    for i, level in enumerate(levels):
        start = 0.0 if i == 0 else (checkpoint_distances[i - 1] + checkpoint_distances[i]) / 2
        end = (
            distance_mi
            if i == last
            else (checkpoint_distances[i] + checkpoint_distances[i + 1]) / 2
        )
        stretch = max(end - start, 0.0)
        miles_by_level[level] = miles_by_level.get(level, 0.0) + stretch
        weighted_score += stretch * level.value

    average = weighted_score / distance_mi if distance_mi > 0 else float(max(levels).value)
    return RouteRiskSummary(
        distance_mi=distance_mi,
        duration_s=duration_s,
        average_risk=average,
        miles_by_level=miles_by_level,
    )


def rank(summaries: Sequence[RouteRiskSummary]) -> list[int]:
    """Indices of ``summaries`` from best to worst (stable for exact ties)."""
    return sorted(range(len(summaries)), key=lambda i: summaries[i].ranking_key)


# --- Explanations -------------------------------------------------------------


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"


def _miles(value: float) -> str:
    return f"{value:,.0f} mi" if value >= 10 else f"{value:.1f} mi"


@dataclass(frozen=True, slots=True)
class _Criterion:
    phrase: str
    value: Callable[[RouteRiskSummary], float]
    fmt: Callable[[float], str]


CRITERIA: tuple[_Criterion, ...] = (
    _Criterion("Avoids No Travel conditions", lambda s: s.ranking_key[0], _miles),
    _Criterion("Fewest Severe-risk miles", lambda s: s.ranking_key[1], _miles),
    _Criterion("Fewest High-risk miles", lambda s: s.ranking_key[2], _miles),
    _Criterion("Lowest average risk", lambda s: s.ranking_key[3], lambda v: f"{v:.2f}"),
    _Criterion("Shortest travel time", lambda s: s.duration_s, format_duration),
)


def explain(
    winner: RouteRiskSummary, runner_up: RouteRiskSummary | None, runner_up_name: str
) -> str:
    """Why ``winner`` ranks above ``runner_up``: the first criterion that separates them."""
    if runner_up is None:
        return "Only one route is available."
    for criterion in CRITERIA:
        best, other = criterion.value(winner), criterion.value(runner_up)
        if best < other:
            return (
                f"{criterion.phrase}: {criterion.fmt(best)} vs "
                f"{criterion.fmt(other)} on {runner_up_name}."
            )
    return f"Ties with {runner_up_name} on every criterion."


def advisory(winner: RouteRiskSummary) -> str:
    """A warning when even the best route is unsafe."""
    if winner.miles(RiskLevel.NO_TRAVEL) > 0:
        return (
            "Every route crosses No Travel conditions at this departure time. "
            "Consider delaying the trip."
        )
    if winner.miles(RiskLevel.SEVERE) > 0:
        return "Every route crosses Severe weather. Drive with extreme caution."
    return ""
