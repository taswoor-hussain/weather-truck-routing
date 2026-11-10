from datetime import datetime, timedelta, timezone

import pytest

from core.geo import LatLon, haversine_mi
from integrations.routing import RouteStep
from integrations.weather import HourlySeries
from trips.domain.checkpoints import (
    build_route_path,
    checkpoint_distances,
    sample_checkpoints,
)
from trips.domain.weather import conditions_at

DEPARTURE = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)
A, B, C = LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)
SEGMENT_MI = haversine_mi(A, B)  # ~69.1 mi
SEGMENT_M = SEGMENT_MI * 1609.344


def step(points, duration_s, distance_m=SEGMENT_M):
    return RouteStep(points=tuple(points), distance_m=distance_m, duration_s=duration_s)


class TestBuildRoutePath:
    def test_stitches_steps_without_duplicating_shared_vertices(self):
        path = build_route_path([step([A, B], 3600), step([B, C], 3600)], max_speed_mph=200)
        assert path.points == (A, B, C)
        assert path.distance_mi == pytest.approx(2 * SEGMENT_MI)
        assert path.duration_s == pytest.approx(7200)

    def test_caps_speed_at_truck_maximum(self):
        # OSRM says 69 mi in 30 min (~138 mph); a 65 mph truck needs longer.
        path = build_route_path([step([A, B], 1800)], max_speed_mph=65)
        assert path.duration_s == pytest.approx(SEGMENT_MI / 65 * 3600)

    def test_slow_steps_keep_their_reported_duration(self):
        path = build_route_path([step([A, B], 3 * 3600)], max_speed_mph=65)
        assert path.duration_s == pytest.approx(3 * 3600)

    def test_step_time_is_distributed_by_segment_length(self):
        midpoint = LatLon(0, 0.25)  # first quarter of the step
        path = build_route_path([step([A, midpoint, B], 4000)], max_speed_mph=200)
        assert path.cumulative_s[1] == pytest.approx(1000, rel=1e-3)

    def test_position_at_interpolates_space_and_time(self):
        path = build_route_path([step([A, B], 3600), step([B, C], 7200)], max_speed_mph=200)
        position, elapsed = path.position_at(SEGMENT_MI * 1.5)
        assert position.lon == pytest.approx(1.5)
        assert elapsed == pytest.approx(3600 + 3600)


class TestCheckpointDistances:
    def test_includes_origin_intervals_and_destination(self):
        assert checkpoint_distances(52.5, 25) == [0, 25, 50, 52.5]

    def test_does_not_duplicate_destination_on_exact_multiple(self):
        assert checkpoint_distances(50, 25) == [0, 25, 50]

    def test_short_route_has_origin_and_destination(self):
        assert checkpoint_distances(4, 10) == [0, 4]


def test_sample_checkpoints_assigns_positions_and_etas():
    path = build_route_path([step([A, B], 3600), step([B, C], 3600)], max_speed_mph=200)
    samples = sample_checkpoints(path, interval_mi=50, departure=DEPARTURE)

    assert [s.sequence for s in samples] == [0, 1, 2, 3]
    assert samples[0].eta == DEPARTURE
    assert samples[-1].position == C
    assert samples[-1].eta == DEPARTURE + timedelta(hours=2)
    assert samples[1].eta == DEPARTURE + timedelta(seconds=50 / SEGMENT_MI * 3600)


class TestConditionsAt:
    start = int(DEPARTURE.timestamp())
    series = HourlySeries(
        times=(start, start + 3600, start + 7200),
        wind_mph=(10, 20, 30),
        rain_in_hr=(0.0, 0.1, 0.2),
        snow_in_hr=(0.0, 1.0, 2.0),
    )

    def test_uses_nearest_hour_for_wind_and_following_hour_for_accumulations(self):
        at_14_20 = conditions_at(self.series, DEPARTURE + timedelta(minutes=20))
        assert at_14_20.wind_mph == 10
        assert at_14_20.rain_in_hr == 0.1
        assert at_14_20.snow_in_hr == 1.0

        at_14_40 = conditions_at(self.series, DEPARTURE + timedelta(minutes=40))
        assert at_14_40.wind_mph == 20

    def test_clamps_to_series_bounds(self):
        late = conditions_at(self.series, DEPARTURE + timedelta(hours=10))
        assert (late.wind_mph, late.rain_in_hr) == (30, 0.2)
