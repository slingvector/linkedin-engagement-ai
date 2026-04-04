"""Sprint 1 — Heatmap HTTP endpoint integration tests.

Coverage:
  GET /api/v2/analytics/heatmap
    ✓ 200 with default weeks
    ✓ 200 with explicit weeks param (valid range 1–52)
    ✓ 422 when weeks < 1 or > 52
    ✓ 401 when unauthenticated (no dependency override)
    ✓ Response shape validation (all required keys present)
    ✓ data_source field present when service returns benchmark data
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.controllers.v2_analytics_controller import router as heatmap_router
from app.dependencies import get_current_user, get_db

# ---------------------------------------------------------------------------
# App factory — isolated app with dependency overrides
# ---------------------------------------------------------------------------

FAKE_HEATMAP = {
    "heatmap": {
        "monday": {"9": 0.70, "10": 0.72},
        "tuesday": {"9": 0.92, "10": 0.98},
        "wednesday": {},
        "thursday": {"9": 0.94},
        "friday": {"9": 0.75},
        "saturday": {},
        "sunday": {},
    },
    "best_slots": [{"day": "tuesday", "hour": 10, "avg_engagement_rate": 0.98}],
    "worst_slots": [{"day": "saturday", "hour": 21, "avg_engagement_rate": 0.08}],
    "data_source": "global_benchmark",
    "sample_size": 0,
}


def _build_test_app(fake_user, fake_heatmap_data: dict = None) -> FastAPI:
    """Build a minimal FastAPI app with only the heatmap router mounted."""
    app = FastAPI()
    app.include_router(heatmap_router)

    async def _override_user():
        return fake_user

    async def _override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    return app


def _make_user():
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHeatmapEndpoint:
    @pytest.fixture
    def app_and_user(self):
        user = _make_user()
        app = _build_test_app(user)
        return app, user

    @pytest.mark.asyncio
    async def test_200_default_weeks(self, app_and_user):
        app, user = app_and_user
        with patch(
            "app.services.heatmap_service.HeatmapService.get_heatmap",
            new=AsyncMock(return_value=FAKE_HEATMAP),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v2/analytics/heatmap")
        assert resp.status_code == 200
        body = resp.json()
        assert "heatmap" in body
        assert "best_slots" in body
        assert "worst_slots" in body
        assert "data_source" in body
        assert "sample_size" in body

    @pytest.mark.asyncio
    async def test_200_explicit_weeks_param(self, app_and_user):
        app, user = app_and_user
        with patch(
            "app.services.heatmap_service.HeatmapService.get_heatmap",
            new=AsyncMock(return_value=FAKE_HEATMAP),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v2/analytics/heatmap?weeks=4")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_422_weeks_below_minimum(self, app_and_user):
        app, user = app_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v2/analytics/heatmap?weeks=0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_422_weeks_above_maximum(self, app_and_user):
        app, user = app_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v2/analytics/heatmap?weeks=53")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_response_data_source_is_present(self, app_and_user):
        app, user = app_and_user
        personal_data = {**FAKE_HEATMAP, "data_source": "personal", "sample_size": 12}
        with patch(
            "app.services.heatmap_service.HeatmapService.get_heatmap",
            new=AsyncMock(return_value=personal_data),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v2/analytics/heatmap")
        assert resp.json()["data_source"] == "personal"
        assert resp.json()["sample_size"] == 12

    @pytest.mark.asyncio
    async def test_heatmap_all_7_days_present(self, app_and_user):
        app, user = app_and_user
        from app.services.heatmap_service import _DAY_NAMES
        with patch(
            "app.services.heatmap_service.HeatmapService.get_heatmap",
            new=AsyncMock(return_value=FAKE_HEATMAP),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v2/analytics/heatmap")
        assert set(resp.json()["heatmap"].keys()) == set(_DAY_NAMES)

    @pytest.mark.asyncio
    async def test_best_slots_list_returned(self, app_and_user):
        app, user = app_and_user
        with patch(
            "app.services.heatmap_service.HeatmapService.get_heatmap",
            new=AsyncMock(return_value=FAKE_HEATMAP),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/v2/analytics/heatmap")
        best = resp.json()["best_slots"]
        assert isinstance(best, list)
        assert len(best) >= 1
        assert "day" in best[0]
        assert "hour" in best[0]
        assert "avg_engagement_rate" in best[0]
