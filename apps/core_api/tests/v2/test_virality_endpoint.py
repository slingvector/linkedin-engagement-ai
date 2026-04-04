"""Sprint 3 — Virality score endpoint integration tests.

Coverage:
  POST /api/v2/posts/{post_id}/score
    ✓ 200 — score returned with full breakdown and hook alternatives
    ✓ 200 — AI engine down: score=None returned (no crash)
    ✓ 404 — post not found
    ✓ Response shape: post_id, virality_score, score_breakdown, hook_alternatives

  GET /api/v2/posts/{post_id}/score
    ✓ 200 — cached score returned
    ✓ 200 — no score yet → virality_score=None, message explains
    ✓ 404 — post not found
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.controllers.v2_posts_controller import router as virality_router
from app.dependencies import get_current_user, get_db

from tests.v2.conftest import make_post, make_virality_score_response, make_uuid


def _make_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


def _build_test_app(user) -> FastAPI:
    app = FastAPI()
    app.include_router(virality_router)

    async def _override_user():
        return user

    async def _override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    return app


class TestScorePostEndpoint:
    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_200_happy_path(self, user):
        post_id = make_uuid()
        post = make_post(
            post_id=post_id,
            user_id=user.id,
            virality_score=74,
            score_breakdown={
                "hook_strength": 22,
                "readability": 18,
                "value_density": 24,
                "cta_quality": 10,
            },
            hook_alternatives=[
                {"hook": "Better hook 1", "predicted_score": 87},
                {"hook": "Better hook 2", "predicted_score": 82},
                {"hook": "Better hook 3", "predicted_score": 79},
            ],
        )
        post.score_updated_at = datetime.now(timezone.utc)

        app = _build_test_app(user)
        with patch(
            "app.services.virality_service.ViralityService.score_post",
            new=AsyncMock(return_value=post),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 200
        body = resp.json()
        assert body["virality_score"] == 74
        assert body["score_breakdown"]["hook_strength"] == 22
        assert len(body["hook_alternatives"]) == 3
        assert body["post_id"] == str(post_id)

    @pytest.mark.asyncio
    async def test_200_ai_engine_down_score_is_none(self, user):
        """Service returns post without score when AI is unavailable."""
        post_id = make_uuid()
        post = make_post(post_id=post_id, user_id=user.id, virality_score=None, score_breakdown=None)

        app = _build_test_app(user)
        with patch(
            "app.services.virality_service.ViralityService.score_post",
            new=AsyncMock(return_value=post),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 200
        assert resp.json()["virality_score"] is None
        assert resp.json()["score_breakdown"] is None

    @pytest.mark.asyncio
    async def test_404_post_not_found(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)
        with patch(
            "app.services.virality_service.ViralityService.score_post",
            new=AsyncMock(side_effect=ValueError(f"Post {post_id} not found")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_response_has_message_field(self, user):
        post_id = make_uuid()
        post = make_post(post_id=post_id, user_id=user.id, virality_score=55)

        app = _build_test_app(user)
        with patch(
            "app.services.virality_service.ViralityService.score_post",
            new=AsyncMock(return_value=post),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/score")

        assert "message" in resp.json()
        assert "55" in resp.json()["message"]


class TestGetScoreEndpoint:
    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_200_cached_score_returned(self, user):
        post_id = make_uuid()
        post = make_post(
            post_id=post_id,
            user_id=user.id,
            virality_score=80,
            score_breakdown={"hook_strength": 25, "readability": 18, "value_density": 27, "cta_quality": 10},
            hook_alternatives=[{"hook": "alt", "predicted_score": 90}],
        )
        post.score_updated_at = datetime.now(timezone.utc)

        app = _build_test_app(user)
        with patch(
            "app.repositories.post_repository.PostRepository.get_by_id",
            new=AsyncMock(return_value=post),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 200
        assert resp.json()["virality_score"] == 80

    @pytest.mark.asyncio
    async def test_200_no_score_yet_message(self, user):
        post_id = make_uuid()
        post = make_post(post_id=post_id, user_id=user.id, virality_score=None)

        app = _build_test_app(user)
        with patch(
            "app.repositories.post_repository.PostRepository.get_by_id",
            new=AsyncMock(return_value=post),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 200
        assert "Not scored yet" in resp.json()["message"] or "POST" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_404_post_not_found(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)
        with patch(
            "app.repositories.post_repository.PostRepository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/v2/posts/{post_id}/score")

        assert resp.status_code == 404
