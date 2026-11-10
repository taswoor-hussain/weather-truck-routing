"""Application error hierarchy.

Every error that can reach an API client derives from :class:`AppError`, which
carries an HTTP status, a stable machine-readable ``code`` and a human message.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    default_message = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class UpstreamServiceError(AppError):
    """A third-party provider (routing, weather, geocoding) failed or timed out."""

    status_code = 502
    code = "upstream_unavailable"
    default_message = "An external service is temporarily unavailable. Please try again."


class NoRouteFound(AppError):
    status_code = 422
    code = "no_route"
    default_message = "No drivable route was found between these locations."
