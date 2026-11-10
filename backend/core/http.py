"""Shared HTTP client for third-party providers.

Wraps a pooled ``requests.Session`` with timeouts and automatic retries on
rate limiting / transient server errors, and converts every transport or
decoding failure into :class:`UpstreamServiceError`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.exceptions import UpstreamServiceError

logger = logging.getLogger(__name__)

RETRY_POLICY = Retry(
    total=3,
    backoff_factor=0.6,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET"}),
    respect_retry_after_header=True,
)


class HttpClient:
    def __init__(self, *, timeout_s: float, user_agent: str, pool_size: int = 16):
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        adapter = HTTPAdapter(
            max_retries=RETRY_POLICY, pool_connections=pool_size, pool_maxsize=pool_size
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        provider: str,
        accept_client_errors: bool = False,
    ) -> Any:
        """GET ``url`` and decode JSON.

        ``accept_client_errors`` returns 4xx bodies instead of raising, for providers
        (like OSRM) that report domain errors such as "no route" as HTTP 400.
        """
        try:
            response = self.session.get(url, params=params, timeout=self.timeout_s)
        except requests.RequestException as exc:
            logger.warning("%s request failed: %s", provider, exc)
            raise UpstreamServiceError(f"{provider} is unreachable.") from exc

        is_accepted_client_error = accept_client_errors and 400 <= response.status_code < 500
        if response.status_code >= 400 and not is_accepted_client_error:
            logger.warning(
                "%s responded %s: %s", provider, response.status_code, response.text[:300]
            )
            raise UpstreamServiceError(
                f"{provider} returned an error.",
                details={"provider": provider, "status": response.status_code},
            )
        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamServiceError(f"{provider} returned an invalid response.") from exc


@lru_cache(maxsize=1)
def default_http_client() -> HttpClient:
    providers = settings.PROVIDERS
    return HttpClient(timeout_s=providers["HTTP_TIMEOUT_S"], user_agent=providers["USER_AGENT"])
