"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health should return 200 with status=healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "core_api"


@pytest.mark.asyncio
async def test_readiness_returns_200(client):
    """GET /readiness should return 200 with status=ready."""
    response = await client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "core_api"
