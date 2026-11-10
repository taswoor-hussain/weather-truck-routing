"""Routing providers. Valhalla (truck costing) is the default; OSRM is a fallback option."""

from django.conf import settings

from core.http import default_http_client
from integrations.routing.osrm import OsrmClient
from integrations.routing.types import RawRoute, RouteStep, RoutingClient
from integrations.routing.valhalla import ValhallaClient

__all__ = ["RawRoute", "RouteStep", "RoutingClient", "get_router"]

_CLIENTS = {"valhalla": ValhallaClient, "osrm": OsrmClient}


def get_router() -> RoutingClient:
    providers = settings.PROVIDERS
    client_class = _CLIENTS[providers["ROUTING_PROVIDER"]]
    return client_class(providers["ROUTING_URL"], default_http_client())
