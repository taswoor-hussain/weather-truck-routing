from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from core.geo import LatLon, haversine_mi
from trips.domain.risk import RiskLevel
from trips.models import Checkpoint, RouteOption, Trip
from trips.services.planner import Location, TripRequest

CHECKPOINT_INTERVALS_MI = (10, 25, 50)
MAX_LOAD_LB = 150_000
MAX_DEPARTURE_AHEAD = timedelta(days=7)
DEPARTURE_GRACE = timedelta(hours=1)
MIN_TRIP_MI = 1


def risk_slug(value: int) -> str:
    return RiskLevel(value).slug


# --- Input ----------------------------------------------------------------------


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class TripRequestSerializer(serializers.Serializer):
    origin = LocationSerializer()
    destination = LocationSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=1, max_value=MAX_LOAD_LB)
    checkpoint_interval_mi = serializers.ChoiceField(choices=CHECKPOINT_INTERVALS_MI)

    def validate_departure_time(self, value):
        now = timezone.now()
        if value < now - DEPARTURE_GRACE:
            raise serializers.ValidationError("Departure time cannot be in the past.")
        if value > now + MAX_DEPARTURE_AHEAD:
            raise serializers.ValidationError("Departure must be within the next 7 days.")
        return value

    def validate(self, attrs):
        origin, destination = attrs["origin"], attrs["destination"]
        distance = haversine_mi(
            LatLon(origin["lat"], origin["lon"]), LatLon(destination["lat"], destination["lon"])
        )
        if distance < MIN_TRIP_MI:
            raise serializers.ValidationError(
                {"destination": "Destination must be different from the origin."}
            )
        return attrs

    def to_request(self) -> TripRequest:
        data = self.validated_data

        def location(raw: dict) -> Location:
            return Location(label=raw["label"], point=LatLon(raw["lat"], raw["lon"]))

        return TripRequest(
            origin=location(data["origin"]),
            destination=location(data["destination"]),
            departure_time=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            checkpoint_interval_mi=int(data["checkpoint_interval_mi"]),
        )


class PlaceQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)


# --- Output ---------------------------------------------------------------------


class CheckpointSerializer(serializers.ModelSerializer):
    risk = serializers.SerializerMethodField()
    factors = serializers.SerializerMethodField()

    class Meta:
        model = Checkpoint
        fields = [
            "sequence",
            "distance_mi",
            "lat",
            "lon",
            "eta",
            "wind_mph",
            "rain_in_hr",
            "snow_in_hr",
            "risk",
            "factors",
            "reasons",
        ]

    def get_risk(self, obj: Checkpoint) -> str:
        return risk_slug(obj.risk_level)

    def get_factors(self, obj: Checkpoint) -> dict[str, str]:
        return {
            "wind": risk_slug(obj.wind_level),
            "rain": risk_slug(obj.rain_level),
            "snow": risk_slug(obj.snow_level),
        }


class RouteOptionSerializer(serializers.ModelSerializer):
    risk_miles = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    checkpoints = CheckpointSerializer(many=True, read_only=True)

    class Meta:
        model = RouteOption
        fields = [
            "id",
            "label",
            "summary",
            "rank",
            "is_recommended",
            "distance_mi",
            "duration_s",
            "arrival_time",
            "average_risk",
            "risk_miles",
            "geometry",
            "checkpoints",
        ]

    def get_risk_miles(self, obj: RouteOption) -> dict[str, float]:
        return {
            RiskLevel.LOW.slug: obj.low_mi,
            RiskLevel.MODERATE.slug: obj.moderate_mi,
            RiskLevel.HIGH.slug: obj.high_mi,
            RiskLevel.SEVERE.slug: obj.severe_mi,
            RiskLevel.NO_TRAVEL.slug: obj.no_travel_mi,
        }

    def get_arrival_time(self, obj: RouteOption):
        arrival = obj.trip.departure_time + timedelta(seconds=obj.duration_s)
        return serializers.DateTimeField().to_representation(arrival)


class TripSerializer(serializers.ModelSerializer):
    origin = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()
    recommendation = serializers.SerializerMethodField()
    routes = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "origin",
            "destination",
            "departure_time",
            "load_weight_lb",
            "checkpoint_interval_mi",
            "recommendation",
            "routes",
            "created_at",
        ]

    def get_origin(self, obj: Trip) -> dict:
        return {"label": obj.origin_label, "lat": obj.origin_lat, "lon": obj.origin_lon}

    def get_destination(self, obj: Trip) -> dict:
        return {
            "label": obj.destination_label,
            "lat": obj.destination_lat,
            "lon": obj.destination_lon,
        }

    def get_recommendation(self, obj: Trip) -> dict:
        best = next((r for r in obj.routes.all() if r.is_recommended), None)
        return {
            "route_id": best.id if best else None,
            "reason": obj.recommendation_reason,
            "advisory": obj.advisory,
        }

    def get_routes(self, obj: Trip) -> list[dict]:
        # Keep the A/B/C order stable in the UI; ``rank`` carries the recommendation order.
        routes = sorted(obj.routes.all(), key=lambda r: r.label)
        return RouteOptionSerializer(routes, many=True).data
