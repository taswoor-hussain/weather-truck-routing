"""Grid of weather sample cells covering the corridor around a trip's routes.

Cells are square in Web-Mercator space (columns spaced evenly in longitude, rows
evenly in Mercator Y), so the client can draw the grid as one image overlay that
lines up exactly with the map. Only cells within ``corridor_mi`` of a route are
included, which keeps weather lookups proportional to the corridor, not its
bounding box.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from core.geo import LatLon, cumulative_distances_mi, haversine_mi, interpolate, locate_along

MILES_PER_DEG_LAT = 69.0
# Coarse on purpose: the client smooths the grid, and every cell costs a forecast lookup.
TARGET_CELLS_LONG_SIDE = 24
MIN_CORRIDOR_MI, MAX_CORRIDOR_MI = 25.0, 75.0
CORRIDOR_SHARE_OF_SPAN = 0.06
ROUTE_SAMPLE_SPACING_MI = 5.0


def mercator_y(lat: float) -> float:
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def inverse_mercator_y(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)


@dataclass(frozen=True, slots=True)
class GridCell:
    row: int
    col: int
    center: LatLon


@dataclass(frozen=True, slots=True)
class CorridorGrid:
    south: float
    west: float
    north: float
    east: float
    rows: int
    cols: int
    cells: tuple[GridCell, ...]


def resample(points: Sequence[LatLon], spacing_mi: float) -> list[LatLon]:
    """Evenly spaced points, at most ``spacing_mi`` apart, including both ends."""
    if len(points) < 2:
        return list(points)
    cumulative = cumulative_distances_mi(points)
    total = cumulative[-1]
    count = max(math.ceil(total / spacing_mi), 1)
    samples = []
    for k in range(count + 1):
        i, fraction = locate_along(cumulative, total * k / count)
        samples.append(interpolate(points[i], points[i + 1], fraction))
    return samples


def corridor_radius_mi(span_mi: float) -> float:
    return min(max(span_mi * CORRIDOR_SHARE_OF_SPAN, MIN_CORRIDOR_MI), MAX_CORRIDOR_MI)


def build_corridor_grid(
    routes: Sequence[Sequence[LatLon]], *, target_cells: int = TARGET_CELLS_LONG_SIDE
) -> CorridorGrid:
    samples = [p for route in routes for p in resample(route, ROUTE_SAMPLE_SPACING_MI)]
    if not samples:
        raise ValueError("At least one route with geometry is required.")

    lats = [p.lat for p in samples]
    lons = [p.lon for p in samples]
    span_mi = haversine_mi(LatLon(min(lats), min(lons)), LatLon(max(lats), max(lons)))
    radius_mi = corridor_radius_mi(span_mi)

    mid_lat = (min(lats) + max(lats)) / 2
    lat_pad = radius_mi / MILES_PER_DEG_LAT
    lon_pad = radius_mi / (MILES_PER_DEG_LAT * math.cos(math.radians(mid_lat)))
    west, east = min(lons) - lon_pad, max(lons) + lon_pad
    y_south, y_north = mercator_y(min(lats) - lat_pad), mercator_y(max(lats) + lat_pad)

    cell = max(east - west, y_north - y_south) / target_cells
    cols = math.ceil((east - west) / cell)
    rows = math.ceil((y_north - y_south) / cell)
    east = west + cols * cell
    y_south = y_north - rows * cell

    def center(row: int, col: int) -> LatLon:
        return LatLon(inverse_mercator_y(y_north - (row + 0.5) * cell), west + (col + 0.5) * cell)

    # Visit only cells near each route sample instead of testing the whole box.
    reach_mi = radius_mi
    included: dict[tuple[int, int], LatLon] = {}
    for point in samples:
        col0 = int((point.lon - west) / cell)
        row0 = int((y_north - mercator_y(point.lat)) / cell)
        cell_mi = cell * MILES_PER_DEG_LAT * math.cos(math.radians(point.lat))
        k = math.ceil(reach_mi / cell_mi) + 1
        for row in range(max(row0 - k, 0), min(row0 + k, rows - 1) + 1):
            for col in range(max(col0 - k, 0), min(col0 + k, cols - 1) + 1):
                if (row, col) in included:
                    continue
                c = center(row, col)
                if haversine_mi(c, point) <= reach_mi:
                    included[(row, col)] = c

    cells = tuple(
        GridCell(row=row, col=col, center=c) for (row, col), c in sorted(included.items())
    )
    return CorridorGrid(
        south=inverse_mercator_y(y_south),
        west=west,
        north=inverse_mercator_y(y_north),
        east=east,
        rows=rows,
        cols=cols,
        cells=cells,
    )
