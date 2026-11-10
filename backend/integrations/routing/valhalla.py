"""Truck routes via Valhalla.

Valhalla's ``truck`` costing uses truck speeds and honours vehicle restrictions
(weight limits, hazmat, etc.), so durations already reflect a heavy vehicle. Each
maneuver provides its time, length and the slice of the leg shape it covers, which
gives maneuver-level speeds for accurate ETAs.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from core.exceptions import NoRouteFound, UpstreamServiceError
from core.geo import LatLon, decode_polyline
from core.http import HttpClient
from integrations.routing.summary import summarise_road_names
from integrations.routing.types import METERS_PER_MILE, PROVIDER, RawRoute, RouteStep

LB_PER_METRIC_TON = 2204.62
# Valhalla error codes meaning "these locations cannot be connected".
NO_ROUTE_ERROR_CODES = {170, 171, 442, 443}


class ValhallaClient:
    def __init__(self, base_url: str, http: HttpClient):
        self.base_url = base_url.rstrip("/")
        self.http = http

    def routes(
        self,
        waypoints: Sequence[LatLon],
        *,
        alternatives: int = 0,
        gross_weight_lb: float | None = None,
    ) -> list[RawRoute]:
        last = len(waypoints) - 1
        request = {
            "locations": [
                # Intermediate points are pass-through: no stop, no U-turn.
                {"lat": p.lat, "lon": p.lon, "type": "break" if i in (0, last) else "through"}
                for i, p in enumerate(waypoints)
            ],
            "costing": "truck",
            "units": "miles",
            "directions_type": "maneuvers",
            "narrative": False,
        }
        if gross_weight_lb:
            request["costing_options"] = {
                "truck": {"weight": round(gross_weight_lb / LB_PER_METRIC_TON, 2)}
            }
        if alternatives:
            request["alternates"] = alternatives

        payload = self.http.get_json(
            f"{self.base_url}/route",
            params={"json": json.dumps(request, separators=(",", ":"))},
            provider=PROVIDER,
            accept_client_errors=True,
        )
        if "trip" not in payload:
            if payload.get("error_code") in NO_ROUTE_ERROR_CODES:
                raise NoRouteFound()
            raise UpstreamServiceError(
                f"{PROVIDER} rejected the request.",
                details={"code": payload.get("error_code"), "message": payload.get("error")},
            )

        trips = [payload["trip"]] + [alt["trip"] for alt in payload.get("alternates", [])]
        return [self._to_route(trip) for trip in trips]

    @staticmethod
    def _to_route(trip: dict) -> RawRoute:
        steps: list[RouteStep] = []
        named_lengths: list[tuple[str, float]] = []
        for leg in trip["legs"]:
            shape = decode_polyline(leg["shape"], precision=6)
            for maneuver in leg["maneuvers"]:
                points = tuple(
                    shape[maneuver["begin_shape_index"] : maneuver["end_shape_index"] + 1]
                )
                if len(points) < 2:
                    continue
                distance_m = float(maneuver["length"]) * METERS_PER_MILE
                steps.append(
                    RouteStep(
                        points=points,
                        distance_m=distance_m,
                        duration_s=float(maneuver["time"]),
                    )
                )
                names = maneuver.get("street_names") or [""]
                named_lengths.append((names[0], distance_m))

        summary = trip["summary"]
        return RawRoute(
            steps=tuple(steps),
            distance_m=float(summary["length"]) * METERS_PER_MILE,
            duration_s=float(summary["time"]),
            summary=summarise_road_names(named_lengths),
        )
