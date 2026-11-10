import pytest

from core.exceptions import UpstreamServiceError
from core.geo import LatLon, haversine_mi
from trips.services.route_options import VIA_OFFSETS, RouteOptionsService, via_points
from trips.tests.fakes import straight_route

ORIGIN, DESTINATION = LatLon(35.0, -100.0), LatLon(35.0, -98.0)
VIAS = via_points(ORIGIN, DESTINATION, VIA_OFFSETS)


class ScriptedRouter:
    """Returns ``direct`` for origin→destination and ``via[i]`` for the i-th via point."""

    def __init__(self, direct, via):
        self.direct = direct
        self.via = dict(zip(VIAS, via, strict=False))

    def routes(self, waypoints, *, alternatives=0, gross_weight_lb=None):
        if len(waypoints) == 2:
            return self.direct
        route = self.via[waypoints[1]]
        if isinstance(route, Exception):
            raise route
        return [route]


def detour(lat, mph=60):
    return straight_route([ORIGIN, LatLon(lat, -99.0), DESTINATION], mph=mph, summary=f"via {lat}")


def test_via_points_are_perpendicular_to_the_trip_on_both_sides():
    north, south = via_points(ORIGIN, DESTINATION, [0.25, -0.25])
    assert north.lat > 35 > south.lat
    assert north.lon == pytest.approx(-99.0)
    assert south.lon == pytest.approx(-99.0)
    assert haversine_mi(north, LatLon(35, -99)) == pytest.approx(
        haversine_mi(south, LatLon(35, -99))
    )


def test_uses_native_alternatives_when_enough():
    routes = [detour(35.0), detour(35.5), detour(34.5)]
    service = RouteOptionsService(ScriptedRouter(routes, via=[]))
    assert len(service.fetch(ORIGIN, DESTINATION, 3)) == 3


def test_tops_up_with_distinct_detours_and_skips_bad_candidates():
    direct = [detour(35.0)]
    candidates = [
        detour(35.001),  # overlaps the direct route → rejected
        UpstreamServiceError(),  # tolerated
        detour(35.6),
        detour(34.4, mph=20),  # far too slow → rejected
    ]
    service = RouteOptionsService(ScriptedRouter(direct, candidates))

    routes = service.fetch(ORIGIN, DESTINATION, 3)

    assert [r.summary for r in routes][0] == "via 35.0"
    assert {r.summary for r in routes} == {"via 35.0", "via 35.6"}


def test_picks_fastest_distinct_detours_and_orders_fastest_first():
    # Via order: north 0.12, south 0.12, north 0.25, south 0.25 (offset fractions).
    candidates = [detour(35.6, mph=40), detour(34.6, mph=58), detour(35.7), detour(34.3)]
    service = RouteOptionsService(ScriptedRouter([detour(35.0)], candidates))

    routes = service.fetch(ORIGIN, DESTINATION, 3)

    # 35.6 is too slow; 35.7 and 34.3 tie on time, so the first-found wins.
    assert [r.summary for r in routes] == ["via 35.0", "via 34.6", "via 35.7"]


def test_returns_fewer_routes_when_no_distinct_detour_exists():
    service = RouteOptionsService(ScriptedRouter([detour(35.0)], [detour(35.0)] * 4))
    assert len(service.fetch(ORIGIN, DESTINATION, 3)) == 1
