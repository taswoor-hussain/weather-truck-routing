import pytest

from trips.domain.risk import (
    RAIN_IN_HR_THRESHOLDS,
    SNOW_IN_HR_THRESHOLDS,
    WIND_MPH_THRESHOLDS,
    RiskLevel,
    WeatherConditions,
    assess,
    classify,
    wind_level_for_load,
)

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)
LIGHT_LOAD = 10_000


@pytest.mark.parametrize(
    ("wind", "expected"),
    [
        (0, L),
        (24.9, L),
        (25, M),
        (34.9, M),
        (35, H),
        (44.9, H),
        (45, S),
        (54.9, S),
        (55, N),
        (80, N),
    ],
)
def test_wind_thresholds(wind, expected):
    assert classify(wind, WIND_MPH_THRESHOLDS) is expected


@pytest.mark.parametrize(
    ("rain", "expected"),
    [
        (0, L),
        (0.09, L),
        (0.10, M),
        (0.24, M),
        (0.25, H),
        (0.49, H),
        (0.50, S),
        (1.00, S),
        (1.01, N),
    ],
)
def test_rain_thresholds(rain, expected):
    assert classify(rain, RAIN_IN_HR_THRESHOLDS) is expected


@pytest.mark.parametrize(
    ("snow", "expected"),
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_thresholds(snow, expected):
    assert classify(snow, SNOW_IN_HR_THRESHOLDS) is expected


class TestLoadRules:
    def test_55_mph_is_no_travel_for_any_load(self):
        assert wind_level_for_load(55, 1)[0] is N

    @pytest.mark.parametrize(("load", "expected"), [(30_000, S), (30_001, N)])
    def test_45_to_54_mph_over_30k_is_no_travel(self, load, expected):
        assert wind_level_for_load(50, load)[0] is expected
        assert wind_level_for_load(54.9, load)[0] is expected

    @pytest.mark.parametrize(("load", "expected"), [(40_000, H), (40_001, S)])
    def test_35_to_44_mph_over_40k_is_severe(self, load, expected):
        assert wind_level_for_load(35, load)[0] is expected
        assert wind_level_for_load(44.9, load)[0] is expected

    def test_load_rules_do_not_touch_lower_winds(self):
        assert wind_level_for_load(34.9, 80_000) == (M, False)

    def test_escalation_is_reported(self):
        assert wind_level_for_load(40, 45_000) == (S, True)
        assert wind_level_for_load(40, 20_000) == (H, False)


class TestAssess:
    def test_calm_weather_is_low_with_no_reasons(self):
        result = assess(WeatherConditions(5, 0, 0), LIGHT_LOAD)
        assert result.level is L
        assert result.reasons == ()

    def test_overall_level_is_worst_factor(self):
        result = assess(WeatherConditions(wind_mph=26, rain_in_hr=0.3, snow_in_hr=2.5), LIGHT_LOAD)
        assert (result.wind_level, result.rain_level, result.snow_level) == (M, H, S)
        assert result.level is S

    def test_reasons_mention_load_when_it_escalates(self):
        result = assess(WeatherConditions(47, 0, 0), 35_000)
        assert result.level is N
        assert result.reasons == ("Wind 47 mph with 35,000 lb load: No Travel",)

    def test_reasons_list_every_contributing_factor(self):
        result = assess(WeatherConditions(10, 0.12, 0.6), LIGHT_LOAD)
        assert result.reasons == ("Rain 0.12 in/hr: Moderate", "Snow 0.60 in/hr: Moderate")


def test_level_labels():
    assert RiskLevel.NO_TRAVEL.label == "No Travel"
    assert RiskLevel.NO_TRAVEL.slug == "no_travel"
