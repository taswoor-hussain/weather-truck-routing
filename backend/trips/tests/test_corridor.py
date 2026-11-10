import pytest

from core.geo import LatLon, haversine_mi
from trips.domain.corridor import (
    TARGET_CELLS_LONG_SIDE,
    build_corridor_grid,
    corridor_radius_mi,
    inverse_mercator_y,
    mercator_y,
    resample,
)

ROUTE = [LatLon(32.78, -96.80), LatLon(37.0, -92.0), LatLon(41.88, -87.63)]


def test_mercator_round_trip():
    for lat in (-60, 0, 32.5, 45, 70):
        assert inverse_mercator_y(mercator_y(lat)) == pytest.approx(lat)


def test_resample_spacing_and_endpoints():
    line = [LatLon(0, 0), LatLon(0, 1)]  # ~69 mi
    samples = resample(line, spacing_mi=10)
    assert samples[0] == line[0]
    assert samples[-1].lon == pytest.approx(1)
    gaps = [haversine_mi(a, b) for a, b in zip(samples, samples[1:], strict=False)]
    assert max(gaps) <= 10.5


def test_corridor_radius_is_bounded():
    assert corridor_radius_mi(10) == 25
    assert corridor_radius_mi(5000) == 75


class TestCorridorGrid:
    grid = build_corridor_grid([ROUTE])

    def test_bounds_contain_the_route(self):
        g = self.grid
        assert g.south < 32.78 and g.north > 41.88
        assert g.west < -96.80 and g.east > -87.63

    def test_long_side_has_target_cell_count(self):
        assert max(self.grid.rows, self.grid.cols) == TARGET_CELLS_LONG_SIDE

    def test_cells_cover_the_route_but_not_the_whole_box(self):
        g = self.grid
        assert 0 < len(g.cells) < g.rows * g.cols * 0.6
        for point in ROUTE:
            nearest = min(haversine_mi(cell.center, point) for cell in g.cells)
            assert nearest < 40

    def test_far_corners_are_excluded(self):
        # Diagonal route: the north-west and south-east corners are far from it.
        indexes = {(c.row, c.col) for c in self.grid.cells}
        assert (0, 0) not in indexes
        assert (self.grid.rows - 1, self.grid.cols - 1) not in indexes

    def test_cells_are_unique_and_in_range(self):
        g = self.grid
        indexes = [(c.row, c.col) for c in g.cells]
        assert len(indexes) == len(set(indexes))
        assert all(0 <= r < g.rows and 0 <= c < g.cols for r, c in indexes)


def test_requires_geometry():
    with pytest.raises(ValueError):
        build_corridor_grid([])
