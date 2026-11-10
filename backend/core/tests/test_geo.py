import pytest

from core.geo import (
    LatLon,
    cumulative_distances_mi,
    decode_polyline,
    haversine_mi,
    interpolate,
    locate_along,
    simplify,
)


def test_haversine_known_distance():
    dallas, chicago = LatLon(32.7767, -96.7970), LatLon(41.8781, -87.6298)
    assert haversine_mi(dallas, chicago) == pytest.approx(802, abs=3)


def test_haversine_zero_for_same_point():
    p = LatLon(10, 10)
    assert haversine_mi(p, p) == 0


def test_cumulative_distances_are_monotonic_and_sum_segments():
    pts = [LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)]
    totals = cumulative_distances_mi(pts)
    assert totals[0] == 0
    assert totals[2] == pytest.approx(2 * totals[1])


def test_locate_along_finds_segment_and_fraction():
    cumulative = [0.0, 10.0, 30.0]
    assert locate_along(cumulative, 0) == (0, 0.0)
    assert locate_along(cumulative, 5) == (0, 0.5)
    assert locate_along(cumulative, 20) == (1, 0.5)
    assert locate_along(cumulative, 30) == (1, 1.0)


def test_locate_along_clamps_out_of_range_distances():
    cumulative = [0.0, 10.0]
    assert locate_along(cumulative, -5) == (0, 0.0)
    assert locate_along(cumulative, 50) == (0, 1.0)


def test_interpolate_midpoint():
    assert interpolate(LatLon(0, 0), LatLon(10, 20), 0.5) == LatLon(5, 10)


def test_decode_polyline_precision_5_reference():
    # Reference example from Google's polyline algorithm documentation.
    points = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5)
    assert [p.as_list() for p in points] == [
        [38.5, -120.2],
        [40.7, -120.95],
        [43.252, -126.453],
    ]


def test_simplify_drops_collinear_points_and_keeps_corners():
    line = [LatLon(0, x / 10) for x in range(11)] + [LatLon(1, 1)]
    simplified = simplify(line, tolerance_deg=0.001)
    assert simplified == [LatLon(0, 0), LatLon(0, 1), LatLon(1, 1)]


def test_rounded_snaps_to_grid():
    assert LatLon(32.7767, -96.797).rounded(0.05) == LatLon(32.8, -96.8)
