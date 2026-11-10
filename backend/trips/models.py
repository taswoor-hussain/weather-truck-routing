import uuid

from django.db import models

from trips.domain.risk import RiskLevel

RISK_LEVEL_CHOICES = [(level.value, level.label) for level in RiskLevel]


class Trip(models.Model):
    """A planned trip: the driver's request plus the recommendation outcome."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    origin_label = models.CharField(max_length=255)
    origin_lat = models.FloatField()
    origin_lon = models.FloatField()
    destination_label = models.CharField(max_length=255)
    destination_lat = models.FloatField()
    destination_lon = models.FloatField()

    departure_time = models.DateTimeField()
    load_weight_lb = models.PositiveIntegerField()
    checkpoint_interval_mi = models.PositiveSmallIntegerField()

    recommendation_reason = models.CharField(max_length=255, blank=True)
    advisory = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.origin_label} → {self.destination_label} ({self.departure_time:%Y-%m-%d %H:%M})"
        )


class RouteOption(models.Model):
    """One of the alternative routes for a trip, with its aggregated risk."""

    trip = models.ForeignKey(Trip, related_name="routes", on_delete=models.CASCADE)
    label = models.CharField(max_length=8)
    summary = models.CharField(max_length=255, blank=True)
    rank = models.PositiveSmallIntegerField()
    is_recommended = models.BooleanField(default=False)

    distance_mi = models.FloatField()
    duration_s = models.FloatField()
    geometry = models.JSONField(help_text="Simplified polyline as [[lat, lon], ...].")

    no_travel_mi = models.FloatField(default=0)
    severe_mi = models.FloatField(default=0)
    high_mi = models.FloatField(default=0)
    moderate_mi = models.FloatField(default=0)
    low_mi = models.FloatField(default=0)
    average_risk = models.FloatField(default=0)

    class Meta:
        ordering = ["rank"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "label"], name="unique_route_label_per_trip"),
        ]

    def __str__(self) -> str:
        return f"Route {self.label} ({self.distance_mi:.0f} mi)"


class Checkpoint(models.Model):
    """A weather sample along a route at the truck's estimated arrival time."""

    route = models.ForeignKey(RouteOption, related_name="checkpoints", on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    distance_mi = models.FloatField()
    lat = models.FloatField()
    lon = models.FloatField()
    eta = models.DateTimeField()

    wind_mph = models.FloatField()
    rain_in_hr = models.FloatField()
    snow_in_hr = models.FloatField()

    risk_level = models.PositiveSmallIntegerField(choices=RISK_LEVEL_CHOICES)
    wind_level = models.PositiveSmallIntegerField(choices=RISK_LEVEL_CHOICES)
    rain_level = models.PositiveSmallIntegerField(choices=RISK_LEVEL_CHOICES)
    snow_level = models.PositiveSmallIntegerField(choices=RISK_LEVEL_CHOICES)
    reasons = models.JSONField(default=list)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "sequence"], name="unique_checkpoint_sequence_per_route"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.route} @ {self.distance_mi:.0f} mi"
