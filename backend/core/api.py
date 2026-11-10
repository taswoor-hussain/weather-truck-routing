"""DRF integration: one consistent error envelope for every failure.

{"error": {"code": "...", "message": "...", "details": {...}}}
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions import AppError

logger = logging.getLogger(__name__)


def error_response(code: str, message: str, status_code: int, details: Any = None) -> Response:
    return Response(
        {"error": {"code": code, "message": message, "details": details or {}}},
        status=status_code,
    )


def exception_handler(exc: Exception, context: dict) -> Response:
    if isinstance(exc, AppError):
        if exc.status_code >= 500:
            logger.warning("%s: %s", exc.code, exc.message)
        return error_response(exc.code, exc.message, exc.status_code, exc.details)

    if isinstance(exc, exceptions.ValidationError):
        return error_response(
            "invalid_request",
            "Some fields are invalid.",
            status.HTTP_400_BAD_REQUEST,
            exc.detail,
        )

    if isinstance(exc, Http404 | exceptions.NotFound):
        return error_response("not_found", "Resource not found.", status.HTTP_404_NOT_FOUND)

    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = getattr(exc, "detail", None)
        return error_response(
            getattr(exc, "default_code", "error"),
            str(detail) if detail else "Request failed.",
            response.status_code,
        )

    logger.exception("Unhandled error", exc_info=exc)
    return error_response(
        AppError.code, AppError.default_message, status.HTTP_500_INTERNAL_SERVER_ERROR
    )
