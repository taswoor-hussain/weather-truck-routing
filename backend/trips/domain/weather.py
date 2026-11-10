"""Reading the forecast at a specific moment (see docs/ARCHITECTURE.md §2.4)."""

from __future__ import annotations

import math
from datetime import datetime

from integrations.weather import HourlySeries
from trips.domain.risk import WeatherConditions

SECONDS_PER_HOUR = 3600


def conditions_at(series: HourlySeries, moment: datetime) -> WeatherConditions:
    """Weather the truck experiences at ``moment``.

    * Wind is instantaneous, so the nearest hourly value is used.
    * Rain/snow values are accumulations over the preceding hour, so the value stamped
      at the *end* of the hour containing ``moment`` is used (14:20 → the 15:00 value).

    Indices are clamped to the series, which the caller requests to cover the trip.
    """
    if not series.times:
        raise ValueError("Empty forecast series.")
    hours_from_start = (moment.timestamp() - series.times[0]) / SECONDS_PER_HOUR
    last = len(series.times) - 1

    nearest = min(max(round(hours_from_start), 0), last)
    bucket_end = min(max(math.floor(hours_from_start) + 1, 0), last)

    return WeatherConditions(
        wind_mph=series.wind_mph[nearest],
        rain_in_hr=series.rain_in_hr[bucket_end],
        snow_in_hr=series.snow_in_hr[bucket_end],
    )
