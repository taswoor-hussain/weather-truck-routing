import json
from datetime import datetime, timezone

import pytest
import responses
from django.core.cache.backends.locmem import LocMemCache

from core.exceptions import NoRouteFound, UpstreamServiceError
from core.geo import LatLon, decode_polyline
from core.http import HttpClient
from integrations.geocoding import PhotonClient
from integrations.routing.osrm import OsrmClient
from integrations.routing.summary import summarise_road_names
from integrations.routing.valhalla import ValhallaClient
from integrations.tests.polyline import encode_polyline
from integrations.weather import OpenMeteoClient

PHOTON_URL = "https://photon.test/api/"
OSRM_URL = "https://osrm.test"
WEATHER_URL = "https://weather.test/v1/forecast"


@pytest.fixture
def http():
    return HttpClient(timeout_s=1, user_agent="tests")


def test_polyline_helper_round_trips():
    coords = [(32.7767, -96.797), (33.0, -96.5)]
    decoded = decode_polyline(encode_polyline(coords))
    assert [(p.lat, p.lon) for p in decoded] == coords


class TestPhoton:
    @responses.activate
    def test_search_builds_labels_and_drops_duplicates(self, http):
        feature = {
            "geometry": {"coordinates": [-96.79, 32.77]},
            "properties": {"name": "Dallas", "state": "Texas", "country": "United States"},
        }
        responses.get(PHOTON_URL, json={"features": [feature, feature, {"geometry": None}]})

        places = PhotonClient(PHOTON_URL, http).search("dallas")

        assert len(places) == 1
        assert places[0].label == "Dallas, Texas, United States"
        assert (places[0].lat, places[0].lon) == (32.77, -96.79)


def osrm_route(name: str, coords: list[tuple[float, float]], duration: float = 600):
    return {
        "distance": 1000.0,
        "duration": duration,
        "legs": [
            {
                "steps": [
                    {
                        "geometry": encode_polyline(coords),
                        "distance": 1000.0,
                        "duration": duration,
                        "name": "Main Street",
                        "ref": name,
                    },
                    # Zero-length arrival step is skipped.
                    {"geometry": encode_polyline(coords[-1:]), "distance": 0, "duration": 0},
                ],
            }
        ],
    }


class TestOsrm:
    @responses.activate
    def test_parses_routes_steps_and_summary(self, http):
        responses.get(
            f"{OSRM_URL}/route/v1/driving/-96.000000,32.000000;-95.000000,33.000000",
            json={"code": "Ok", "routes": [osrm_route("I 30; US 67", [(32, -96), (33, -95)])]},
        )

        routes = OsrmClient(OSRM_URL, http).routes(
            [LatLon(32, -96), LatLon(33, -95)], alternatives=2
        )

        assert len(routes) == 1
        route = routes[0]
        assert route.summary == "I 30"
        assert len(route.steps) == 1
        assert route.steps[0].points == (LatLon(32, -96), LatLon(33, -95))
        assert responses.calls[0].request.params["alternatives"] == "2"

    @responses.activate
    def test_via_requests_forbid_u_turns(self, http):
        responses.get(
            f"{OSRM_URL}/route/v1/driving/-96.000000,32.000000;-95.500000,32.500000;-95.000000,33.000000",
            json={"code": "Ok", "routes": [osrm_route("US 75", [(32, -96), (33, -95)])]},
        )
        OsrmClient(OSRM_URL, http).routes([LatLon(32, -96), LatLon(32.5, -95.5), LatLon(33, -95)])
        params = responses.calls[0].request.params
        assert params["continue_straight"] == "true"
        assert params["alternatives"] == "false"

    @responses.activate
    def test_no_route_maps_to_domain_error(self, http):
        responses.get(
            f"{OSRM_URL}/route/v1/driving/-96.000000,32.000000;10.000000,50.000000",
            json={"code": "NoRoute", "message": "Impossible route"},
            status=400,
        )
        with pytest.raises(NoRouteFound):
            OsrmClient(OSRM_URL, http).routes([LatLon(32, -96), LatLon(50, 10)])

    @responses.activate
    def test_server_error_maps_to_upstream_error(self, http):
        responses.get(
            f"{OSRM_URL}/route/v1/driving/-96.000000,32.000000;-95.000000,33.000000",
            status=503,
        )
        with pytest.raises(UpstreamServiceError):
            OsrmClient(OSRM_URL, http).routes([LatLon(32, -96), LatLon(33, -95)])


def test_summary_lists_longest_roads_in_driving_order():
    steps = [
        ("Elm St", 1),
        ("I 30; US 67", 300),
        ("Ramp", 2),
        ("I 57", 200),
        ("US 60", 50),
        ("", 9),
    ]
    assert summarise_road_names(steps) == "I 30, I 57, US 60"


VALHALLA_URL = "https://valhalla.test"


def valhalla_trip(time_s: float = 3600, length_mi: float = 60.0):
    shape = encode_polyline([(32, -96), (32.5, -95.5), (33, -95)])
    return {
        "summary": {"time": time_s, "length": length_mi},
        "legs": [
            {
                "shape": shape,
                "maneuvers": [
                    {
                        "begin_shape_index": 0,
                        "end_shape_index": 2,
                        "time": time_s,
                        "length": length_mi,
                        "street_names": ["I 35E", "Stemmons Freeway"],
                    },
                    {"begin_shape_index": 2, "end_shape_index": 2, "time": 0, "length": 0},
                ],
            }
        ],
    }


class TestValhalla:
    @responses.activate
    def test_parses_trip_and_alternates_with_truck_weight(self, http):
        responses.get(
            f"{VALHALLA_URL}/route",
            json={"trip": valhalla_trip(), "alternates": [{"trip": valhalla_trip(4000)}]},
        )

        routes = ValhallaClient(VALHALLA_URL, http).routes(
            [LatLon(32, -96), LatLon(33, -95)], alternatives=2, gross_weight_lb=77_000
        )

        assert [r.duration_s for r in routes] == [3600, 4000]
        route = routes[0]
        assert route.summary == "I 35E"
        assert route.distance_m == pytest.approx(60 * 1609.344)
        assert len(route.steps) == 1  # zero-length arrival maneuver dropped
        assert route.steps[0].points[1] == LatLon(32.5, -95.5)

        request = json.loads(responses.calls[0].request.params["json"])
        assert request["costing"] == "truck"
        assert request["alternates"] == 2
        assert request["costing_options"]["truck"]["weight"] == pytest.approx(34.93, abs=0.01)
        assert [loc["type"] for loc in request["locations"]] == ["break", "break"]

    @responses.activate
    def test_via_points_are_pass_through(self, http):
        responses.get(f"{VALHALLA_URL}/route", json={"trip": valhalla_trip()})
        ValhallaClient(VALHALLA_URL, http).routes(
            [LatLon(32, -96), LatLon(32.5, -95), LatLon(33, -95)]
        )
        request = json.loads(responses.calls[0].request.params["json"])
        assert [loc["type"] for loc in request["locations"]] == ["break", "through", "break"]
        assert "alternates" not in request

    @responses.activate
    def test_no_path_maps_to_no_route(self, http):
        responses.get(
            f"{VALHALLA_URL}/route",
            json={"error_code": 442, "error": "No path could be found for input"},
            status=400,
        )
        with pytest.raises(NoRouteFound):
            ValhallaClient(VALHALLA_URL, http).routes([LatLon(32, -96), LatLon(50, 10)])

    @responses.activate
    def test_other_errors_map_to_upstream_error(self, http):
        responses.get(
            f"{VALHALLA_URL}/route", json={"error_code": 154, "error": "Too far"}, status=400
        )
        with pytest.raises(UpstreamServiceError):
            ValhallaClient(VALHALLA_URL, http).routes([LatLon(32, -96), LatLon(33, -95)])


def forecast(times, wind, rain, showers, snow):
    return {
        "hourly": {
            "time": times,
            "wind_speed_10m": wind,
            "rain": rain,
            "showers": showers,
            "snowfall": snow,
        }
    }


class TestOpenMeteo:
    START = datetime(2026, 11, 10, 12, 30, tzinfo=timezone.utc)
    END = datetime(2026, 11, 10, 13, 10, tzinfo=timezone.utc)

    def client(self, http):
        cache = LocMemCache("weather-tests", {})
        cache.clear()
        return OpenMeteoClient(WEATHER_URL, http, cache=cache, cache_ttl_s=60)

    @responses.activate
    def test_combines_rain_and_showers_and_aligns_with_points(self, http):
        responses.get(
            WEATHER_URL,
            json=[
                forecast([0, 3600], [10, 20], [0.1, 0.2], [0.05, None], [0, 1]),
                forecast([0, 3600], [30, 40], [0, 0], [0, 0], [0, 0]),
            ],
        )
        points = [LatLon(32.01, -96.01), LatLon(40.0, -90.0)]

        series = self.client(http).hourly(points, self.START, self.END)

        assert series[0].rain_in_hr == pytest.approx((0.15, 0.2))
        assert series[0].snow_in_hr == (0.0, 1.0)
        assert series[1].wind_mph == (30.0, 40.0)
        params = responses.calls[0].request.params
        assert params["start_hour"] == "2026-11-10T12:00"
        assert params["end_hour"] == "2026-11-10T13:00"
        assert params["latitude"] == "32.0000,40.0000"

    @responses.activate
    def test_nearby_points_share_one_lookup_and_results_are_cached(self, http):
        responses.get(WEATHER_URL, json=forecast([0], [10], [0], [0], [0]))
        client = self.client(http)
        points = [LatLon(32.001, -96.001), LatLon(32.002, -96.002)]

        first = client.hourly(points, self.START, self.END)
        second = client.hourly(points, self.START, self.END)

        assert len(responses.calls) == 1
        assert first == second
        assert first[0] is first[1]

    @responses.activate
    def test_malformed_payload_raises_upstream_error(self, http):
        responses.get(WEATHER_URL, json={"hourly": {"time": [0]}})
        with pytest.raises(UpstreamServiceError):
            self.client(http).hourly([LatLon(1, 1)], self.START, self.END)
