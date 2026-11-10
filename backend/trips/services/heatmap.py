"""Weather-risk heatmap for a trip corridor, hourly from departure to +48 h."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache

from core.geo import LatLon
from integrations.weather import OpenMeteoClient, get_weather_client
from trips.domain.corridor import build_corridor_grid
from trips.domain.risk import factor_levels
from trips.domain.weather import conditions_at
from trips.models import Trip


def _hour_floor(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


class CorridorHeatmapService:
    def __init__(self, weather: OpenMeteoClient | None = None, *, hours: int | None = None):
        self.weather = weather or get_weather_client()
        self.hours = hours or settings.PLANNING["HEATMAP_HOURS"]

    def for_trip(self, trip: Trip) -> dict:
        key = f"heatmap:{trip.pk}:{self.hours}"
        result = cache.get(key)
        if result is None:
            result = self._build(trip)
            cache.set(key, result, timeout=settings.PLANNING["WEATHER_CACHE_TTL_S"])
        return result

    def _build(self, trip: Trip) -> dict:
        routes = [[LatLon(lat, lon) for lat, lon in route.geometry] for route in trip.routes.all()]
        grid = build_corridor_grid(routes)

        start = _hour_floor(trip.departure_time)
        moments = [start + timedelta(hours=h) for h in range(self.hours + 1)]
        # +1 h so the last hour's precipitation bucket is available.
        series = self.weather.hourly(
            [cell.center for cell in grid.cells], start, moments[-1] + timedelta(hours=1)
        )
        load = trip.load_weight_lb

        return {
            "bounds": {
                "south": grid.south,
                "west": grid.west,
                "north": grid.north,
                "east": grid.east,
            },
            "rows": grid.rows,
            "cols": grid.cols,
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "hours": len(moments),
            "cells": [
                {
                    "row": cell.row,
                    "col": cell.col,
                    "risk": [
                        int(factor_levels(conditions_at(cell_series, moment), load).overall)
                        for moment in moments
                    ],
                }
                for cell, cell_series in zip(grid.cells, series, strict=True)
            ],
        }
