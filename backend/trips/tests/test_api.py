from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.exceptions import UpstreamServiceError
from core.geo import LatLon
from integrations.geocoding import Place
from trips.models import Checkpoint, Trip
from trips.services.planner import TripPlanner
from trips.tests.fakes import FakeRouter, FakeWeather, straight_route

ORIGIN = LatLon(35.0, -100.0)
DESTINATION = LatLon(35.0, -98.0)  # ~113 mi due east


@pytest.fixture
def client():
    return APIClient()


def payload(**overrides):
    body = {
        "origin": {"label": "Origin", "lat": ORIGIN.lat, "lon": ORIGIN.lon},
        "destination": {"label": "Destination", "lat": DESTINATION.lat, "lon": DESTINATION.lon},
        "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_weight_lb": 42_000,
        "checkpoint_interval_mi": 25,
    }
    body.update(overrides)
    return body


def three_routes():
    north = LatLon(35.5, -99.0)
    south = LatLon(34.5, -99.0)
    return [
        straight_route([ORIGIN, DESTINATION], mph=60, summary="I 40"),
        straight_route([ORIGIN, north, DESTINATION], mph=60, summary="US 60"),
        straight_route([ORIGIN, south, DESTINATION], mph=60, summary="US 62"),
    ]


def use_providers(router, weather):
    return mock.patch(
        "trips.views.TripPlanner",
        side_effect=lambda: TripPlanner(router=router, weather=weather),
    )


@pytest.mark.django_db
class TestCreateTrip:
    def test_plans_three_routes_with_checkpoints_and_recommends_fastest_when_calm(self, client):
        router = FakeRouter(three_routes())
        with use_providers(router, FakeWeather()):
            response = client.post("/api/trips", payload(), format="json")

        assert response.status_code == 201, response.data
        data = response.json()
        assert [r["label"] for r in data["routes"]] == ["A", "B", "C"]
        recommended = [r for r in data["routes"] if r["is_recommended"]]
        assert len(recommended) == 1
        assert recommended[0]["summary"] == "I 40"
        assert data["recommendation"]["route_id"] == recommended[0]["id"]
        assert data["recommendation"]["reason"].startswith("Shortest travel time")

        checkpoints = recommended[0]["checkpoints"]
        assert [c["distance_mi"] for c in checkpoints[:3]] == [0, 25, 50]
        assert checkpoints[0]["risk"] == "low"
        assert checkpoints[1]["eta"] > checkpoints[0]["eta"]
        # Truck routing receives the gross weight (tare + load).
        assert router.calls[0]["weight"] == 35_000 + 42_000

    def test_heavy_load_in_high_wind_avoids_route_through_storm(self, client):
        # 40 mph east of -98.9 → High; with >40,000 lb the load rule makes it Severe.
        # The southern detour stays west of the storm for longer.
        weather = FakeWeather(storm_east_of_lon=-98.9, storm_wind_mph=40)
        with use_providers(FakeRouter(three_routes()), weather):
            data = client.post("/api/trips", payload(), format="json").json()

        severe = {r["label"]: r["risk_miles"]["severe"] for r in data["routes"]}
        best = next(r for r in data["routes"] if r["is_recommended"])
        assert severe[best["label"]] == min(severe.values())
        assert "Severe" in data["recommendation"]["advisory"]
        stormy = [c for c in best["checkpoints"] if c["risk"] == "severe"]
        assert stormy
        assert stormy[0]["factors"]["wind"] == "severe"
        assert "42,000 lb load" in stormy[0]["reasons"][0]

    def test_persists_trip_graph(self, client):
        with use_providers(FakeRouter(three_routes()), FakeWeather()):
            trip_id = client.post("/api/trips", payload(), format="json").json()["id"]
        trip = Trip.objects.get(pk=trip_id)
        assert trip.routes.count() == 3
        assert Checkpoint.objects.filter(route__trip=trip).count() > 3

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"load_weight_lb": 0}, "load_weight_lb"),
            ({"checkpoint_interval_mi": 15}, "checkpoint_interval_mi"),
            ({"departure_time": "2020-01-01T00:00:00Z"}, "departure_time"),
            (
                {"destination": {"label": "Same", "lat": ORIGIN.lat, "lon": ORIGIN.lon}},
                "destination",
            ),
        ],
    )
    def test_rejects_invalid_requests(self, client, overrides, field):
        response = client.post("/api/trips", payload(**overrides), format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_request"
        assert field in response.json()["error"]["details"]

    def test_upstream_failure_returns_502(self, client):
        router = mock.Mock()
        router.routes.side_effect = UpstreamServiceError()
        with use_providers(router, FakeWeather()):
            response = client.post("/api/trips", payload(), format="json")
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "upstream_unavailable"


@pytest.mark.django_db
class TestGetTrip:
    def test_returns_saved_plan(self, client):
        with use_providers(FakeRouter(three_routes()), FakeWeather()):
            created = client.post("/api/trips", payload(), format="json").json()
        response = client.get(f"/api/trips/{created['id']}")
        assert response.status_code == 200
        assert response.json() == created

    def test_unknown_trip_is_404(self, client):
        response = client.get("/api/trips/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestPlaceSearch:
    def test_returns_places(self, client):
        geocoder = mock.Mock()
        geocoder.search.return_value = [Place("Dallas, Texas, United States", 32.7, -96.8)]
        with mock.patch("trips.views.get_geocoder", return_value=geocoder):
            response = client.get("/api/places", {"q": "dal"})
        assert response.status_code == 200
        assert response.json() == [
            {"label": "Dallas, Texas, United States", "lat": 32.7, "lon": -96.8}
        ]

    def test_requires_two_characters(self, client):
        assert client.get("/api/places", {"q": "d"}).status_code == 400


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


@pytest.mark.django_db
class TestHeatmap:
    def test_returns_hourly_risk_grid_for_corridor(self, client):
        weather = FakeWeather(storm_east_of_lon=-98.5, storm_wind_mph=60)
        with use_providers(FakeRouter(three_routes()), weather):
            trip_id = client.post("/api/trips", payload(), format="json").json()["id"]

        with mock.patch("trips.services.heatmap.get_weather_client", return_value=weather):
            response = client.get(f"/api/trips/{trip_id}/heatmap")

        assert response.status_code == 200
        data = response.json()
        assert data["hours"] == 49
        assert data["start_time"].endswith(":00:00Z")
        assert data["cells"]
        assert all(len(cell["risk"]) == 49 for cell in data["cells"])
        assert {cell["risk"][0] for cell in data["cells"]} == {0, 4}  # calm vs >= 55 mph


def test_spa_fallback_serves_index(client, settings, tmp_path):
    (tmp_path / "index.html").write_text("<div id=root></div>")
    settings.FRONTEND_DIST_DIR = tmp_path
    response = client.get("/some/client/route")
    assert response.status_code == 200
    assert b"root" in b"".join(response.streaming_content)


def test_unknown_api_path_is_not_swallowed_by_spa(client):
    assert client.get("/api/does-not-exist").status_code == 404


@pytest.mark.django_db
def test_planning_is_throttled(client):
    router, weather = FakeRouter(three_routes()), FakeWeather()
    with use_providers(router, weather):
        statuses = [
            client.post("/api/trips", payload(), format="json").status_code for _ in range(13)
        ]
    assert statuses[:12] == [201] * 12
    assert statuses[12] == 429
