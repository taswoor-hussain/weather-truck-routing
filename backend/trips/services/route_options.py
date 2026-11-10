"""Obtain N distinct route options between two points.

The provider's native alternatives are tried first. Long trips often yield fewer than
requested, so the set is topped up by routing through via points offset
perpendicular to the straight origin→destination line. Candidates that mostly
overlap an existing route, or that are unreasonably long detours, are discarded.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from core.exceptions import AppError, NoRouteFound
from core.geo import LatLon
from integrations.routing import RawRoute, RoutingClient

logger = logging.getLogger(__name__)

# Perpendicular offsets of the via point, as a fraction of the straight-line distance.
VIA_OFFSETS = (0.12, -0.12, 0.25, -0.25)
MAX_DETOUR_RATIO = 1.5  # vs the fastest route's duration
MAX_OVERLAP = 0.8  # share of road two routes may have in common
MAX_CONCURRENT_REQUESTS = 2  # stay polite with public routing servers
OVERLAP_GRID_DEG = 0.02  # ~1.5 km cells used to compare route footprints


def via_points(origin: LatLon, destination: LatLon, offsets: Sequence[float]) -> list[LatLon]:
    """Points beside the midpoint of the origin→destination line, on either side."""
    mid_lat = (origin.lat + destination.lat) / 2
    mid_lon = (origin.lon + destination.lon) / 2
    # Work in a locally isotropic plane (scale longitude by cos(latitude)).
    k = math.cos(math.radians(mid_lat))
    dx, dy = (destination.lon - origin.lon) * k, destination.lat - origin.lat
    return [LatLon(mid_lat + dx * f, mid_lon - dy * f / k) for f in offsets]


def footprint(route: RawRoute) -> set[tuple[int, int]]:
    return {
        (round(p.lat / OVERLAP_GRID_DEG), round(p.lon / OVERLAP_GRID_DEG))
        for step in route.steps
        for p in step.points
    }


def overlap(a: set, b: set) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 1.0


class RouteOptionsService:
    def __init__(self, router: RoutingClient):
        self.router = router

    def fetch(
        self,
        origin: LatLon,
        destination: LatLon,
        count: int,
        *,
        gross_weight_lb: float | None = None,
    ) -> list[RawRoute]:
        """Up to ``count`` distinct routes, fastest first."""
        routes = self.router.routes(
            [origin, destination], alternatives=count - 1, gross_weight_lb=gross_weight_lb
        )
        if not routes:
            raise NoRouteFound()

        selected = [(route, footprint(route)) for route in routes[:count]]
        if len(selected) < count:
            fastest = min(route.duration_s for route, _ in selected)
            for candidate in self._via_candidates(origin, destination, gross_weight_lb):
                if len(selected) >= count:
                    break
                if candidate.duration_s > fastest * MAX_DETOUR_RATIO:
                    continue
                shape = footprint(candidate)
                if all(overlap(shape, other) < MAX_OVERLAP for _, other in selected):
                    selected.append((candidate, shape))

        if len(selected) < count:
            logger.info("Only %d distinct routes found (wanted %d)", len(selected), count)
        return sorted((route for route, _ in selected), key=lambda r: r.duration_s)

    def _via_candidates(
        self, origin: LatLon, destination: LatLon, gross_weight_lb: float | None
    ) -> list[RawRoute]:
        """Fastest-first detour routes; failures of individual detours are tolerated."""
        vias = via_points(origin, destination, VIA_OFFSETS)

        def route_via(via: LatLon) -> RawRoute | None:
            try:
                routes = self.router.routes(
                    [origin, via, destination], gross_weight_lb=gross_weight_lb
                )
            except AppError as exc:
                logger.info("Via-point route skipped: %s", exc.message)
                return None
            return routes[0] if routes else None

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as pool:
            candidates = [route for route in pool.map(route_via, vias) if route]
        return sorted(candidates, key=lambda r: r.duration_s)
