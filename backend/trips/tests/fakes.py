"""In-memory stand-ins for external providers, for service and API tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.geo import LatLon, cumulative_distances_mi
from integrations.routing import RawRoute, RouteStep
from integrations.weather import HourlySeries

METERS_PER_MILE = 1609.344


def straight_route(points: list[LatLon], mph: float, summary: str) -> RawRoute:
    miles = cumulative_distances_mi(points)[-1]
    duration = miles / mph * 3600
    step = RouteStep(points=tuple(points), distance_m=miles * METERS_PER_MILE, duration_s=duration)
    return RawRoute(
        steps=(step,), distance_m=miles * METERS_PER_MILE, duration_s=duration, summary=summary
    )


class FakeRouter:
    def __init__(self, routes: list[RawRoute]):
        self._routes = routes
        self.calls: list[dict] = []

    def routes(self, waypoints, *, alternatives=0, gross_weight_lb=None):
        self.calls.append(
            {"waypoints": waypoints, "alternatives": alternatives, "weight": gross_weight_lb}
        )
        return self._routes[: alternatives + 1]


class FakeWeather:
    """Calm everywhere, except the given wind speed east of ``storm_east_of_lon``."""

    def __init__(self, storm_east_of_lon: float | None = None, storm_wind_mph: float = 0):
        self.storm_east_of_lon = storm_east_of_lon
        self.storm_wind_mph = storm_wind_mph

    def hourly(self, points, start: datetime, end: datetime) -> list[HourlySeries]:
        first = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        hours = int((end - first) / timedelta(hours=1)) + 1
        times = tuple(int((first + timedelta(hours=h)).timestamp()) for h in range(hours))
        return [self._series(point, times) for point in points]

    def _series(self, point: LatLon, times: tuple[int, ...]) -> HourlySeries:
        stormy = self.storm_east_of_lon is not None and point.lon > self.storm_east_of_lon
        wind = self.storm_wind_mph if stormy else 5.0
        zeros = (0.0,) * len(times)
        return HourlySeries(
            times=times, wind_mph=(wind,) * len(times), rain_in_hr=zeros, snow_in_hr=zeros
        )
