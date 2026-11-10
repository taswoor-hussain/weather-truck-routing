from rest_framework import exceptions

from core.api import exception_handler
from core.exceptions import NoRouteFound, UpstreamServiceError


def test_app_error_is_wrapped_in_envelope():
    response = exception_handler(NoRouteFound(), {})
    assert response.status_code == 422
    assert response.data["error"]["code"] == "no_route"


def test_upstream_error_maps_to_502_with_details():
    response = exception_handler(UpstreamServiceError("down", details={"provider": "osrm"}), {})
    assert response.status_code == 502
    assert response.data["error"] == {
        "code": "upstream_unavailable",
        "message": "down",
        "details": {"provider": "osrm"},
    }


def test_validation_error_exposes_field_details():
    response = exception_handler(exceptions.ValidationError({"load_weight_lb": ["Required"]}), {})
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_request"
    assert "load_weight_lb" in response.data["error"]["details"]


def test_unexpected_error_returns_generic_500():
    response = exception_handler(RuntimeError("boom"), {})
    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert "boom" not in response.data["error"]["message"]
