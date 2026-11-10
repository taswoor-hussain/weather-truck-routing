"""Small, dependency-free geometry helpers (WGS84 lat/lon, miles)."""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

EARTH_RADIUS_MI = 3958.7613


@dataclass(frozen=True, slots=True)
class LatLon:
    lat: float
    lon: float

    def rounded(self, step: float) -> LatLon:
        """Snap to a regular grid of ``step`` degrees (used for de-duplication/caching)."""
        return LatLon(
            round(round(self.lat / step) * step, 6), round(round(self.lon / step) * step, 6)
        )

    def as_list(self, precision: int = 5) -> list[float]:
        return [round(self.lat, precision), round(self.lon, precision)]


def haversine_mi(a: LatLon, b: LatLon) -> float:
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    d_phi = phi2 - phi1
    d_lambda = math.radians(b.lon - a.lon)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def cumulative_distances_mi(points: Sequence[LatLon]) -> list[float]:
    """Distance from the first point to each point along the polyline."""
    totals = [0.0]
    for previous, current in zip(points, points[1:], strict=False):
        totals.append(totals[-1] + haversine_mi(previous, current))
    return totals


def interpolate(a: LatLon, b: LatLon, fraction: float) -> LatLon:
    """Linear interpolation; accurate enough for the short segments of a road polyline."""
    return LatLon(a.lat + (b.lat - a.lat) * fraction, a.lon + (b.lon - a.lon) * fraction)


def locate_along(cumulative: Sequence[float], distance: float) -> tuple[int, float]:
    """Find the segment containing ``distance`` along a polyline.

    Returns ``(i, fraction)`` such that the position lies between vertex ``i`` and
    ``i + 1`` at ``fraction`` of that segment. ``distance`` is clamped to the line.
    """
    if len(cumulative) < 2:
        return 0, 0.0
    distance = min(max(distance, 0.0), cumulative[-1])
    i = min(bisect_right(cumulative, distance) - 1, len(cumulative) - 2)
    span = cumulative[i + 1] - cumulative[i]
    return i, (distance - cumulative[i]) / span if span > 0 else 0.0


def decode_polyline(encoded: str, precision: int = 6) -> list[LatLon]:
    """Decode a Google encoded polyline (OSRM ``polyline6`` uses precision 6)."""
    factor = 10**precision
    points: list[LatLon] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append(LatLon(lat / factor, lon / factor))
    return points


def simplify(points: Sequence[LatLon], tolerance_deg: float) -> list[LatLon]:
    """Ramer–Douglas–Peucker simplification (iterative, planar in degrees)."""
    if len(points) < 3:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    tolerance_sq = tolerance_deg**2

    while stack:
        start, end = stack.pop()
        a, b = points[start], points[end]
        dx, dy = b.lon - a.lon, b.lat - a.lat
        norm_sq = dx * dx + dy * dy
        max_dist_sq, max_index = 0.0, -1
        for i in range(start + 1, end):
            p = points[i]
            if norm_sq == 0:
                dist_sq = (p.lon - a.lon) ** 2 + (p.lat - a.lat) ** 2
            else:
                cross = dx * (p.lat - a.lat) - dy * (p.lon - a.lon)
                dist_sq = cross * cross / norm_sq
            if dist_sq > max_dist_sq:
                max_dist_sq, max_index = dist_sq, i
        if max_dist_sq > tolerance_sq:
            keep[max_index] = True
            stack.append((start, max_index))
            stack.append((max_index, end))

    return [p for p, kept in zip(points, keep, strict=True) if kept]
