"""Read-side queries for trips."""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from trips.models import Trip


def trips_with_routes() -> QuerySet[Trip]:
    return Trip.objects.prefetch_related("routes__checkpoints")


def get_trip(trip_id) -> Trip:
    return get_object_or_404(trips_with_routes(), pk=trip_id)
