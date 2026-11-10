"""Place search via Photon (OpenStreetMap), which is built for autocomplete."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from core.http import HttpClient, default_http_client

PROVIDER = "Geocoding service"


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    lat: float
    lon: float


class PhotonClient:
    def __init__(self, base_url: str, http: HttpClient):
        self.base_url = base_url
        self.http = http

    def search(self, query: str, limit: int = 6) -> list[Place]:
        payload = self.http.get_json(
            self.base_url,
            params={"q": query, "limit": limit, "lang": "en"},
            provider=PROVIDER,
        )
        places: list[Place] = []
        seen: set[str] = set()
        for feature in payload.get("features", []):
            place = self._to_place(feature)
            if place and place.label not in seen:
                seen.add(place.label)
                places.append(place)
        return places

    @staticmethod
    def _to_place(feature: dict) -> Place | None:
        try:
            lon, lat = feature["geometry"]["coordinates"][:2]
        except (KeyError, TypeError, ValueError):
            return None
        props = feature.get("properties", {})
        parts: list[str] = []
        for key in ("name", "city", "state", "country"):
            value = props.get(key)
            if value and value not in parts:
                parts.append(value)
        if not parts:
            return None
        return Place(label=", ".join(parts), lat=float(lat), lon=float(lon))


def get_geocoder() -> PhotonClient:
    return PhotonClient(settings.PROVIDERS["GEOCODING_URL"], default_http_client())
