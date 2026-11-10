"""Hourly forecasts via Open-Meteo.

Many locations are fetched per request (Open-Meteo accepts coordinate lists),
batches run concurrently, and each location's series is cached so overlapping
routes and repeated plans don't hit the provider again.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache as default_cache

from core.exceptions import UpstreamServiceError
from core.geo import LatLon
from core.http import HttpClient, default_http_client

logger = logging.getLogger(__name__)

PROVIDER = "Weather service"
HOURLY_VARIABLES = "wind_speed_10m,rain,showers,snowfall"
# Forecast models resolve ~3–13 km; snapping points to this grid lets nearby
# checkpoints (and overlapping routes) share one lookup.
GRID_STEP_DEG = 0.05
BATCH_SIZE = 50
MAX_CONCURRENT_BATCHES = 4


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """Hourly values for one location.

    ``times`` are UTC epoch seconds on the hour. Wind is instantaneous at that time;
    rain and snow are accumulations over the *preceding* hour (Open-Meteo semantics).
    """

    times: tuple[int, ...]
    wind_mph: tuple[float, ...]
    rain_in_hr: tuple[float, ...]
    snow_in_hr: tuple[float, ...]


def _hour_param(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00")


def _numbers(values: list | None) -> tuple[float, ...]:
    # Open-Meteo uses null when a model has no value for an hour; treat as no hazard.
    return tuple(float(v) if v is not None else 0.0 for v in (values or []))


class OpenMeteoClient:
    def __init__(self, base_url: str, http: HttpClient, *, cache=default_cache, cache_ttl_s: int):
        self.base_url = base_url
        self.http = http
        self.cache = cache
        self.cache_ttl_s = cache_ttl_s

    def hourly(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlySeries]:
        """Series for each point covering the whole hours from ``start`` to ``end``.

        The result is aligned with ``points``.
        """
        window = (_hour_param(start), _hour_param(end))
        snapped = [p.rounded(GRID_STEP_DEG) for p in points]
        keys = [self._cache_key(p, window) for p in snapped]
        cached: dict[str, HourlySeries] = self.cache.get_many(list(set(keys)))

        missing: dict[str, LatLon] = {}
        for key, point in zip(keys, snapped, strict=True):
            if key not in cached:
                missing.setdefault(key, point)
        pending = list(missing.items())
        batches = [pending[i : i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
        if batches:
            logger.info("Fetching weather for %d locations (%d cached)", len(pending), len(cached))
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as pool:
                results = pool.map(
                    lambda batch: self._fetch([p for _, p in batch], window), batches
                )
                fetched: dict[str, HourlySeries] = {}
                for batch, series in zip(batches, results, strict=True):
                    fetched.update({key: s for (key, _), s in zip(batch, series, strict=True)})
            self.cache.set_many(fetched, timeout=self.cache_ttl_s)
            cached.update(fetched)

        return [cached[key] for key in keys]

    def _fetch(self, points: Sequence[LatLon], window: tuple[str, str]) -> list[HourlySeries]:
        payload = self.http.get_json(
            self.base_url,
            params={
                "latitude": ",".join(f"{p.lat:.4f}" for p in points),
                "longitude": ",".join(f"{p.lon:.4f}" for p in points),
                "hourly": HOURLY_VARIABLES,
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "GMT",
                "timeformat": "unixtime",
                "start_hour": window[0],
                "end_hour": window[1],
            },
            provider=PROVIDER,
        )
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(points):
            raise UpstreamServiceError(f"{PROVIDER} returned an unexpected number of locations.")
        return [self._to_series(location) for location in locations]

    @staticmethod
    def _to_series(location: dict) -> HourlySeries:
        try:
            hourly = location["hourly"]
            rain = _numbers(hourly["rain"])
            showers = _numbers(hourly["showers"])
            return HourlySeries(
                times=tuple(int(t) for t in hourly["time"]),
                wind_mph=_numbers(hourly["wind_speed_10m"]),
                rain_in_hr=tuple(r + s for r, s in zip(rain, showers, strict=True)),
                snow_in_hr=_numbers(hourly["snowfall"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamServiceError(f"{PROVIDER} returned an invalid forecast.") from exc

    @staticmethod
    def _cache_key(point: LatLon, window: tuple[str, str]) -> str:
        return f"wx:{point.lat:.4f}:{point.lon:.4f}:{window[0]}:{window[1]}"


def get_weather_client() -> OpenMeteoClient:
    return OpenMeteoClient(
        settings.PROVIDERS["WEATHER_URL"],
        default_http_client(),
        cache_ttl_s=settings.PLANNING["WEATHER_CACHE_TTL_S"],
    )
