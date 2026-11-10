"""Driving routes via OSRM.

Routes are requested with ``steps=true`` (and no full overview geometry): each
step carries its own geometry, distance and duration, which gives step-level
speeds for accurate ETAs at a fraction of the cost of per-segment annotations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.conf import settings

from core.exceptions import NoRouteFound, UpstreamServiceError
from core.geo import LatLon, decode_polyline
from core.http import HttpClient, default_http_client

PROVIDER = "Routing service"
NO_ROUTE_CODES = {"NoRoute", "NoSegment"}


@dataclass(frozen=True, slots=True)
class RouteStep:
    points: tuple[LatLon, ...]
    distance_m: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class RawRoute:
    steps: tuple[RouteStep, ...]
    distance_m: float
    duration_s: float
    summary: str


class OsrmClient:
    def __init__(self, base_url: str, http: HttpClient):
        self.base_url = base_url.rstrip("/")
        self.http = http

    def routes(self, waypoints: Sequence[LatLon], *, alternatives: int = 0) -> list[RawRoute]:
        """Fastest route through ``waypoints`` plus up to ``alternatives`` alternatives."""
        coordinates = ";".join(f"{p.lon:.6f},{p.lat:.6f}" for p in waypoints)
        params = {
            "alternatives": str(alternatives) if alternatives else "false",
            "overview": "false",
            "steps": "true",
            "geometries": "polyline6",
        }
        if len(waypoints) > 2:
            # Forbid U-turns at via points, which would otherwise create spurious detours.
            params["continue_straight"] = "true"

        payload = self.http.get_json(
            f"{self.base_url}/route/v1/driving/{coordinates}",
            params=params,
            provider=PROVIDER,
            accept_client_errors=True,
        )
        code = payload.get("code")
        if code in NO_ROUTE_CODES:
            raise NoRouteFound()
        if code != "Ok":
            raise UpstreamServiceError(f"{PROVIDER} rejected the request.", details={"code": code})
        return [self._to_route(route) for route in payload.get("routes", [])]

    @staticmethod
    def _to_route(route: dict) -> RawRoute:
        steps: list[RouteStep] = []
        summaries: list[str] = []
        for leg in route["legs"]:
            for name in (leg.get("summary") or "").split(", "):
                if name and name not in summaries:
                    summaries.append(name)
            for step in leg["steps"]:
                points = tuple(decode_polyline(step["geometry"], precision=6))
                if len(points) >= 2:
                    steps.append(
                        RouteStep(
                            points=points,
                            distance_m=float(step["distance"]),
                            duration_s=float(step["duration"]),
                        )
                    )
        return RawRoute(
            steps=tuple(steps),
            distance_m=float(route["distance"]),
            duration_s=float(route["duration"]),
            summary=", ".join(summaries),
        )


def get_router() -> OsrmClient:
    return OsrmClient(settings.PROVIDERS["ROUTING_URL"], default_http_client())
