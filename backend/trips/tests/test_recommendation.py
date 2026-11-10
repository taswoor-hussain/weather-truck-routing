import pytest

from trips.domain.recommendation import (
    RouteRiskSummary,
    advisory,
    explain,
    format_duration,
    rank,
    summarise_route,
)
from trips.domain.risk import RiskLevel

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


def summary(*, no_travel=0.0, severe=0.0, high=0.0, avg=0.0, hours=10.0):
    return RouteRiskSummary(
        distance_mi=500,
        duration_s=hours * 3600,
        average_risk=avg,
        miles_by_level={N: no_travel, S: severe, H: high},
    )


class TestSummariseRoute:
    def test_each_checkpoint_covers_half_way_to_neighbours(self):
        result = summarise_route([0, 10, 20, 25], [L, S, L, H], distance_mi=25, duration_s=1)
        # Stretches: [0,5] L, [5,15] S, [15,22.5] L, [22.5,25] H
        assert result.miles(L) == pytest.approx(12.5)
        assert result.miles(S) == pytest.approx(10)
        assert result.miles(H) == pytest.approx(2.5)
        assert sum(result.miles_by_level.values()) == pytest.approx(25)

    def test_average_is_distance_weighted(self):
        result = summarise_route([0, 10, 20], [L, S, L], distance_mi=20, duration_s=1)
        assert result.average_risk == pytest.approx(10 * 3 / 20)

    def test_rejects_mismatched_inputs(self):
        with pytest.raises(ValueError):
            summarise_route([0, 10], [L], distance_mi=10, duration_s=1)


class TestRank:
    def test_no_travel_miles_dominate_everything(self):
        routes = [summary(no_travel=5, hours=5), summary(severe=100, hours=20)]
        assert rank(routes) == [1, 0]

    def test_severe_miles_first(self):
        assert rank([summary(severe=20), summary(severe=10, high=300)]) == [1, 0]

    def test_then_high_miles(self):
        assert rank([summary(severe=10, high=50), summary(severe=10, high=20, avg=2)]) == [1, 0]

    def test_then_average_risk(self):
        assert rank([summary(avg=0.5, hours=8), summary(avg=0.2, hours=12)]) == [1, 0]

    def test_then_travel_time(self):
        assert rank([summary(hours=12), summary(hours=11), summary(hours=13)]) == [1, 0, 2]

    def test_floating_point_noise_does_not_decide(self):
        routes = [summary(severe=10.00001, hours=9), summary(severe=10.0, hours=10)]
        assert rank(routes) == [0, 1]


class TestExplain:
    def test_names_first_deciding_criterion(self):
        text = explain(summary(severe=0, high=90), summary(severe=42), "Route B")
        assert text == "Fewest Severe-risk miles: 0.0 mi vs 42 mi on Route B."

    def test_falls_through_to_travel_time(self):
        text = explain(summary(hours=10), summary(hours=11.5), "Route C")
        assert text == "Shortest travel time: 10 h 00 min vs 11 h 30 min on Route C."

    def test_single_route(self):
        assert explain(summary(), None, "") == "Only one route is available."


class TestAdvisory:
    def test_warns_when_best_route_has_no_travel_miles(self):
        assert "No Travel" in advisory(summary(no_travel=3))

    def test_cautions_on_severe(self):
        assert "Severe" in advisory(summary(severe=3))

    def test_silent_when_safe(self):
        assert advisory(summary(high=30)) == ""


def test_format_duration():
    assert format_duration(45 * 60) == "45 min"
    assert format_duration(3 * 3600 + 5 * 60) == "3 h 05 min"
