"""Unit and API integration tests for error hierarchy and standardized error contracts."""

import pytest

from askbase.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)


def test_error_hierarchy_status_codes():
    """Verify operational error status codes and default error codes."""
    val = ValidationError("Invalid field", details=[{"field": "email", "message": "invalid"}])
    assert val.status_code == 400
    assert val.code == "VALIDATION_ERROR"
    assert val.to_dict()["error"]["code"] == "VALIDATION_ERROR"
    assert len(val.to_dict()["error"]["details"]) == 1

    bad = BadRequestError("Malformed syntax")
    assert bad.status_code == 400
    assert bad.code == "BAD_REQUEST"

    unauth = UnauthorizedError("Missing token")
    assert unauth.status_code == 401
    assert unauth.code == "UNAUTHORIZED"

    forbid = ForbiddenError("Access forbidden")
    assert forbid.status_code == 403
    assert forbid.code == "FORBIDDEN"

    nf = NotFoundError("Item not found")
    assert nf.status_code == 404
    assert nf.code == "NOT_FOUND"

    conf = ConflictError("Unique key violation")
    assert conf.status_code == 409
    assert conf.code == "RESOURCE_CONFLICT"

    svc = ServiceUnavailableError("DB disconnected")
    assert svc.status_code == 503
    assert svc.code == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_api_404_standardized_format(app_client):
    """Verify undefined routes return standardized 404 NOT_FOUND JSON."""
    res = await app_client.get("/api/unknown-endpoint-12345")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_api_validation_error_format(app_client):
    """Verify request validation returns standardized 400 VALIDATION_ERROR JSON."""
    res = await app_client.post("/api/auth/register", json={"email": "not-an-email"})
    assert res.status_code == 400
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
