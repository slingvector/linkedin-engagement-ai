"""Sprint 4 — Carousel endpoint integration tests.

Coverage:
  POST /api/v2/posts/{post_id}/carousel
    ✓ 201 — generated successfully, returns CarouselAssetResponse
    ✓ 404 — post not found (service raises ValueError)
    ✓ 502 — AI Engine failed (service raises RuntimeError)
    ✓ Response shape validation (id, post_id, slide_count, slides, status)

  GET /api/v2/posts/{post_id}/carousel
    ✓ 200 — asset found
    ✓ 404 — no carousel generated yet

  POST /api/v2/posts/{post_id}/carousel/publish
    ✓ 200 — published to LinkedIn, returns li_post_urn
    ✓ 404 — no carousel found
    ✓ 400 — missing LinkedIn OAuth token
    ✓ 400 — token decryption failed
    ✓ 404 — asset not found / PDF missing (service raises ValueError/FileNotFoundError)
    ✓ 502 — LinkedIn API failure
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.controllers.v2_carousel_controller import router as carousel_router
from app.dependencies import get_current_user, get_db

from tests.v2.conftest import (
    make_uuid,
    make_post,
    make_carousel_asset,
    _default_slides,
)


def _make_user(has_token: bool = True):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.access_token_encrypted = b"encrypted_token" if has_token else None
    return user


def _build_test_app(user) -> FastAPI:
    app = FastAPI()
    app.include_router(carousel_router)

    async def _override_user():
        return user

    async def _override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    return app


# Mock asset that get_by_post returns — must have all fields
def _mock_asset(post_id: uuid.UUID) -> MagicMock:
    asset = make_carousel_asset(post_id=post_id)
    return asset


# ---------------------------------------------------------------------------
# POST /carousel (generate)
# ---------------------------------------------------------------------------


class TestGenerateCarouselEndpoint:
    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_201_generated(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.create_carousel",
            new=AsyncMock(return_value=asset),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/carousel")

        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert "post_id" in body
        assert "slide_count" in body
        assert "slides" in body
        assert "status" in body

    @pytest.mark.asyncio
    async def test_404_post_not_found(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.create_carousel",
            new=AsyncMock(side_effect=ValueError(f"Post {post_id} not found")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/carousel")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_502_ai_engine_failed(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.create_carousel",
            new=AsyncMock(side_effect=RuntimeError("AI Engine failed to generate carousel outline")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/carousel")

        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_response_slides_shape(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.create_carousel",
            new=AsyncMock(return_value=asset),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v2/posts/{post_id}/carousel")

        slides = resp.json()["slides"]
        assert isinstance(slides, list)
        for slide in slides:
            assert "slide_number" in slide
            assert "headline" in slide
            assert "body" in slide
            assert "visual_suggestion" in slide


# ---------------------------------------------------------------------------
# GET /carousel
# ---------------------------------------------------------------------------


class TestGetCarouselEndpoint:
    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_200_asset_found(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.get_by_post",
            new=AsyncMock(return_value=asset),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/v2/posts/{post_id}/carousel")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_404_no_carousel_generated(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.get_by_post",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/v2/posts/{post_id}/carousel")

        assert resp.status_code == 404
        assert "No carousel" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /carousel/publish
# ---------------------------------------------------------------------------


class TestPublishCarouselEndpoint:
    @pytest.fixture
    def user(self):
        return _make_user(has_token=True)

    @pytest.fixture
    def user_no_token(self):
        return _make_user(has_token=False)

    @pytest.mark.asyncio
    async def test_200_published_successfully(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with (
            patch(
                "app.services.carousel_service.CarouselService.get_by_post",
                new=AsyncMock(return_value=asset),
            ),
            patch(
                "app.services.carousel_service.CarouselService.publish_to_linkedin",
                new=AsyncMock(return_value="urn:li:share:9999"),
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "My amazing carousel!"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["linkedin_post_urn"] == "urn:li:share:9999"
        assert "published successfully" in body["message"]

    @pytest.mark.asyncio
    async def test_404_no_carousel_to_publish(self, user):
        post_id = make_uuid()
        app = _build_test_app(user)

        with patch(
            "app.services.carousel_service.CarouselService.get_by_post",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "text"},
                )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_400_missing_linkedin_token(self, user_no_token):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user_no_token)

        with (
            patch(
                "app.services.carousel_service.CarouselService.get_by_post",
                new=AsyncMock(return_value=asset),
            ),
            patch(
                "app.services.carousel_service.CarouselService.publish_to_linkedin",
                new=AsyncMock(side_effect=ValueError("write_flow_not_connected")),
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "text"},
                )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_400_token_decryption_failure(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with (
            patch(
                "app.services.carousel_service.CarouselService.get_by_post",
                new=AsyncMock(return_value=asset),
            ),
            patch(
                "app.services.carousel_service.CarouselService.publish_to_linkedin",
                new=AsyncMock(side_effect=ValueError("Decryption failed")),
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "text"},
                )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_404_pdf_file_missing(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with (
            patch(
                "app.services.carousel_service.CarouselService.get_by_post",
                new=AsyncMock(return_value=asset),
            ),
            patch(
                "app.services.carousel_service.CarouselService.publish_to_linkedin",
                new=AsyncMock(side_effect=FileNotFoundError("PDF not found")),
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "text"},
                )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_502_linkedin_api_failure(self, user):
        post_id = make_uuid()
        asset = _mock_asset(post_id)
        app = _build_test_app(user)

        with (
            patch(
                "app.services.carousel_service.CarouselService.get_by_post",
                new=AsyncMock(return_value=asset),
            ),
            patch(
                "app.services.carousel_service.CarouselService.publish_to_linkedin",
                new=AsyncMock(side_effect=Exception("LinkedIn API rate limit")),
            ),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v2/posts/{post_id}/carousel/publish",
                    json={"post_text": "text"},
                )

        assert resp.status_code == 502
        assert "LinkedIn publish failed" in resp.json()["detail"]
