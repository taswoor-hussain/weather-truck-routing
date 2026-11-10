"""Route timing and checkpoint sampling.

A :class:`RoutePath` is the route polyline annotated with cumulative distance and
cumulative *truck* travel time at every vertex, so any point along the route can be
placed in space and time.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.geo import LatLon, haversine_mi, interpolate, locate_along
from integrations.routing import RouteStep

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, slots=True)
class RoutePath:
    points: tuple[LatLon, ...]
    cumulative_mi: tuple[float, ...]
    cumulative_s: tuple[float, ...]

    @property
    def distance_mi(self) -> float:
        return self.cumulative_mi[-1]

    @property
    def duration_s(self) -> float:
        return self.cumulative_s[-1]

    def position_at(self, distance_mi: float) -> tuple[LatLon, float]:
        """Location and elapsed seconds at ``distance_mi`` from the start."""
        i, fraction = locate_along(self.cumulative_mi, distance_mi)
        if len(self.points) == 1:
            return self.points[0], 0.0
        position = interpolate(self.points[i], self.points[i + 1], fraction)
        elapsed = (
            self.cumulative_s[i] + (self.cumulative_s[i + 1] - self.cumulative_s[i]) * fraction
        )
        return position, elapsed


@dataclass(frozen=True, slots=True)
class CheckpointSample:
    sequence: int
    distance_mi: float
    position: LatLon
    eta: datetime


def build_route_path(steps: Sequence[RouteStep], max_speed_mph: float) -> RoutePath:
    """Stitch step geometries into one path and spread each step's duration over it.

    Each step's speed is capped at ``max_speed_mph`` (a safety net for car-profile
    providers whose highway speeds exceed truck limits), and its time is distributed
    proportionally to the length of its segments.
    """
    points: list[LatLon] = []
    cumulative_mi: list[float] = []
    cumulative_s: list[float] = []

    for step in steps:
        step_points = list(step.points)
        if points and step_points[0] == points[-1]:
            step_points = step_points[1:]
        if not points:
            points.append(step_points[0])
            cumulative_mi.append(0.0)
            cumulative_s.append(0.0)
            step_points = step_points[1:]

        lengths = []
        previous = points[-1]
        for point in step_points:
            lengths.append(haversine_mi(previous, point))
            previous = point
        step_length = sum(lengths)

        min_duration = (step.distance_m / METERS_PER_MILE) / max_speed_mph * SECONDS_PER_HOUR
        duration = max(step.duration_s, min_duration)

        for point, length in zip(step_points, lengths, strict=True):
            points.append(point)
            cumulative_mi.append(cumulative_mi[-1] + length)
            share = length / step_length if step_length > 0 else 0.0
            cumulative_s.append(cumulative_s[-1] + duration * share)

    if not points:
        raise ValueError("Route has no geometry.")
    return RoutePath(tuple(points), tuple(cumulative_mi), tuple(cumulative_s))


def checkpoint_distances(total_mi: float, interval_mi: float) -> list[float]:
    """Origin, every ``interval_mi`` along the route, and the destination."""
    distances = [0.0]
    mark = interval_mi
    while mark < total_mi:
        distances.append(mark)
        mark += interval_mi
    if total_mi > 0:
        distances.append(total_mi)
    return distances


def sample_checkpoints(
    path: RoutePath, interval_mi: float, departure: datetime
) -> list[CheckpointSample]:
    samples = []
    for sequence, distance in enumerate(checkpoint_distances(path.distance_mi, interval_mi)):
        position, elapsed_s = path.position_at(distance)
        samples.append(
            CheckpointSample(
                sequence=sequence,
                distance_mi=distance,
                position=position,
                eta=departure + timedelta(seconds=elapsed_s),
            )
        )
    return samples
