"""Integration tests for process health and database readiness probes."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_root_metadata_endpoint(app_client):
    """Verify GET / returns API operational metadata."""
    res = await app_client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "AskBase API"
    assert data["status"] == "operational"
    assert "version" in data


@pytest.mark.asyncio
async def test_liveness_probe_endpoints(app_client):
    """Verify /health/live and legacy /health return process liveness."""
    for path in ["/health/live", "/health"]:
        res = await app_client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "uptime" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_healthy(app_client):
    """Verify /health/ready and /ready return 200 when database is healthy."""
    for path in ["/health/ready", "/ready"]:
        res = await app_client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["database"]["status"] == "connected"
        assert isinstance(data["database"]["latencyMs"], (int, float))


@pytest.mark.asyncio
async def test_readiness_probe_degraded(app_client):
    """Verify /health/ready returns 503 Service Unavailable when DB is unreachable."""
    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        side_effect=Exception("Connection timed out"),
    ):
        res = await app_client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "disconnected"
        assert "Connection timed out" in data["database"]["error"]
