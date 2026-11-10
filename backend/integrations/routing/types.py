"""Provider-neutral routing types."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from core.geo import LatLon

PROVIDER = "Routing service"
METERS_PER_MILE = 1609.344


@dataclass(frozen=True, slots=True)
class RouteStep:
    """A stretch of road with homogeneous timing (an OSRM step / Valhalla maneuver)."""

    points: tuple[LatLon, ...]
    distance_m: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class RawRoute:
    steps: tuple[RouteStep, ...]
    distance_m: float
    duration_s: float
    summary: str


class RoutingClient(Protocol):
    def routes(
        self,
        waypoints: Sequence[LatLon],
        *,
        alternatives: int = 0,
        gross_weight_lb: float | None = None,
    ) -> list[RawRoute]:
        """Best route through ``waypoints`` plus up to ``alternatives`` alternatives."""
        ...
