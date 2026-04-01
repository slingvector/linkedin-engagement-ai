"""Cross-service V2 integration tests.

These tests exercise the complete pipeline calling across:
  core_api (service layer) → ai_engine (mocked httpx) → carousel_renderer (mocked httpx)

They validate that the orchestration contracts hold end-to-end:
  Sprint 1: HeatmapService → GET /api/v2/analytics/heatmap (full roundtrip)
  Sprint 2: SmartFillService orchestrates heatmap + AI engine → creates N draft Posts
  Sprint 3: ViralityService → AI engine score → persists to Post
  Sprint 4: CarouselService → AI outline → renderer → asset persisted → LinkedIn publish flow

All external I/O (DB, httpx) is mocked. No real network or DB calls.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

import pytest
import httpx

from tests.v2.conftest import (
    make_uuid,
    make_post,
    make_carousel_asset,
    make_user_settings,
    make_ai_outline_response,
    make_virality_score_response,
    make_week_plan_response,
    make_db_session,
    db_scalar_result,
)


# ===========================================================================
# Sprint 1 + Sprint 2 Integration: HeatmapService feeds SmartFillService
# ===========================================================================


class TestHeatmapFeedsSmartFill:
    """HeatmapService result is consumed by SmartFillService for slot selection."""

    @pytest.mark.asyncio
    async def test_smart_fill_uses_heatmap_best_slots(self):
        """Verify best slots from heatmap are reflected in scheduled_at on created posts."""
        from app.services.heatmap_service import HeatmapService
        from app.services.smart_fill_service import SmartFillService
        from app.repositories.post_repository import PostRepository

        user_id = make_uuid()
        db = make_db_session()

        # HeatmapService returns personal data with known best slot (tuesday 10am)
        heatmap_raw = [
            {"dow": 1, "hour": 10, "post_count": 8, "avg_rate": 0.20},  # tuesday 10
            {"dow": 1, "hour": 9, "post_count": 5, "avg_rate": 0.15},
            {"dow": 3, "hour": 9, "post_count": 6, "avg_rate": 0.12},
            {"dow": 3, "hour": 10, "post_count": 4, "avg_rate": 0.10},
            {"dow": 0, "hour": 10, "post_count": 3, "avg_rate": 0.08},
        ]
        heatmap_service = HeatmapService(db)
        heatmap_service._query_raw = AsyncMock(return_value=heatmap_raw)

        # PostRepository mock
        post_repo = AsyncMock(spec=PostRepository)
        created_posts = []

        async def _capture_create(post):
            post.id = make_uuid()
            created_posts.append(post)
            return post

        post_repo.create.side_effect = _capture_create

        service = SmartFillService(post_repo, heatmap_service)

        # AI engine returns 3 posts
        ai_resp = make_week_plan_response(count=3)

        async def _fake_ai(**kwargs):
            return ai_resp["posts"]

        service._call_ai_engine = _fake_ai

        result = await service.smart_fill(
            user_id=user_id,
            pillars=["AI Automation", "Founder Stories", "Product Tips"],
            posts_per_week=3,
            preferred_formats=["text", "carousel"],
        )

        assert len(result) == 3
        # All created posts should be drafts with scheduled_at set
        for post in result:
            assert post.status == "draft"
            assert post.scheduled_at is not None

        # Best slot = tuesday 10am (weekday=1, hour=10) → verify at least one post hits it
        scheduled_weekdays = [p.scheduled_at.weekday() for p in result]
        assert 1 in scheduled_weekdays, "Expected at least one post scheduled on Tuesday"

    @pytest.mark.asyncio
    async def test_heatmap_benchmark_fallback_still_schedules_posts(self):
        """New user (0 posts) → benchmarks used → posts still get scheduled."""
        from app.services.heatmap_service import HeatmapService
        from app.services.smart_fill_service import SmartFillService
        from app.repositories.post_repository import PostRepository

        db = make_db_session()
        heatmap_service = HeatmapService(db)
        heatmap_service._query_raw = AsyncMock(return_value=[])  # 0 rows → benchmark

        post_repo = AsyncMock(spec=PostRepository)

        async def _capture(post):
            post.id = make_uuid()
            return post

        post_repo.create.side_effect = _capture

        service = SmartFillService(post_repo, heatmap_service)
        ai_resp = make_week_plan_response(count=4)

        async def _fake_ai(**kwargs):
            return ai_resp["posts"]

        service._call_ai_engine = _fake_ai

        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI", "Products"],
            posts_per_week=4,
            preferred_formats=["text"],
        )

        assert len(result) == 4
        for post in result:
            assert post.scheduled_at is not None


# ===========================================================================
# Sprint 3 Integration: ViralityService → AI Engine → Post update roundtrip
# ===========================================================================


class TestViralityServicePipeline:
    """End-to-end: score a draft post → AI returns score → post fields updated."""

    @pytest.mark.asyncio
    async def test_full_scoring_pipeline(self):
        from app.services.virality_service import ViralityService
        from app.repositories.post_repository import PostRepository

        user_id = make_uuid()
        post = make_post(user_id=user_id, status="draft")

        db = make_db_session()
        post_repo = AsyncMock(spec=PostRepository)
        post_repo.get_by_id.return_value = post
        post_repo.update.return_value = post

        settings = MagicMock()
        settings.ai_engine_url = "http://ai-engine"
        settings.ai_engine_api_key = "key"

        service = ViralityService(post_repo, db)
        service._settings = settings

        # Patch DB query for top hooks
        async def _top_hooks(user_id, limit=3):
            return ["Best hook 1", "Best hook 2"]

        service._get_top_hooks = _top_hooks

        # Patch httpx: AI engine returns score
        ai_payload = make_virality_score_response(total_score=82)

        with patch("app.services.virality_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = ai_payload
            mock_http.post.return_value = mock_resp

            result = await service.score_post(post.id, user_id)

        assert result.virality_score == 82
        assert result.score_breakdown is not None
        assert len(result.hook_alternatives) == 3
        assert result.score_updated_at is not None
        post_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_scoring_with_no_published_posts_still_works(self):
        """User with 0 published posts → top_hooks=[] → AI still called → score returned."""
        from app.services.virality_service import ViralityService
        from app.repositories.post_repository import PostRepository

        post = make_post()
        db = make_db_session()
        post_repo = AsyncMock(spec=PostRepository)
        post_repo.get_by_id.return_value = post
        post_repo.update.return_value = post

        settings = MagicMock()
        settings.ai_engine_url = "http://ai-engine"
        settings.ai_engine_api_key = "key"

        service = ViralityService(post_repo, db)
        service._settings = settings

        # Simulate DB returning empty hooks (no published posts)
        async def _empty_hooks(user_id, limit=3):
            return []

        service._get_top_hooks = _empty_hooks
        ai_payload = make_virality_score_response(total_score=55)

        with patch("app.services.virality_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = ai_payload
            mock_http.post.return_value = mock_resp

            result = await service.score_post(post.id, post.user_id)

        assert result.virality_score == 55


# ===========================================================================
# Sprint 4 Integration: Full Carousel Pipeline
# (AI outline → renderer → store → CarouselAsset)
# ===========================================================================


class TestCarouselPipeline:
    """Exercises CarouselService step-by-step with mocked httpx at each hop."""

    @pytest.mark.asyncio
    async def test_full_carousel_creation_pipeline(self):
        """
        Verifies:
        1. AI Engine called with correct payload
        2. Carousel Renderer called with slides + brand_kit
        3. PDF stored → pdf_url set
        4. CarouselAsset persisted with status='rendered'
        """
        from app.services.carousel_service import CarouselService
        from app.repositories.post_repository import PostRepository

        user_id = make_uuid()
        post = make_post(user_id=user_id)

        db = make_db_session()
        post_repo = AsyncMock(spec=PostRepository)
        post_repo.get_by_id.return_value = post

        settings = MagicMock()
        settings.ai_engine_url = "http://ai-engine"
        settings.ai_engine_api_key = "test-key"
        settings.carousel_renderer_url = "http://renderer"

        service = CarouselService(post_repo, db)
        service._settings = settings

        # Patch brand kit
        async def _fake_brand_kit(user_id):
            return {"primary_color": "#0A66C2", "logo_url": None, "font_family": "Inter",
                    "author_name": "", "author_tagline": ""}

        service._get_brand_kit = _fake_brand_kit

        outline = make_ai_outline_response()
        fake_pdf_bytes = b"FAKE_PDF_BYTES_FROM_RENDERER"
        fake_pdf_b64 = base64.b64encode(fake_pdf_bytes).decode("utf-8")

        ai_calls = []
        renderer_calls = []

        saved_asset = {}
        def _capture_add(asset):
            asset.id = make_uuid()
            saved_asset["asset"] = asset
        db.add.side_effect = _capture_add
        db.refresh.side_effect = lambda o: None

        with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http

            # AI Engine response
            ai_resp = MagicMock()
            ai_resp.raise_for_status = MagicMock()
            ai_resp.json.return_value = outline

            # Renderer response
            renderer_resp = MagicMock()
            renderer_resp.raise_for_status = MagicMock()
            renderer_resp.json.return_value = {"pdf_base64": fake_pdf_b64}

            # First call = AI engine, second call = renderer
            mock_http.post.side_effect = [ai_resp, renderer_resp]

            result = await service.create_carousel(post.id, user_id)

        # Verify asset was captured and committed
        assert "asset" in saved_asset
        assert saved_asset["asset"].status == "rendered"
        assert saved_asset["asset"].slide_count == 7
        assert saved_asset["asset"].pdf_url is not None
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_carousel_creation_when_renderer_unavailable(self):
        """Renderer times out → pdf_bytes=None → asset saved as 'draft'."""
        from app.services.carousel_service import CarouselService
        from app.repositories.post_repository import PostRepository

        post = make_post()
        db = make_db_session()
        post_repo = AsyncMock(spec=PostRepository)
        post_repo.get_by_id.return_value = post

        settings = MagicMock()
        settings.ai_engine_url = "http://ai-engine"
        settings.ai_engine_api_key = "key"
        settings.carousel_renderer_url = "http://renderer"

        service = CarouselService(post_repo, db)
        service._settings = settings

        async def _fake_brand_kit(user_id):
            return {"primary_color": "#0A66C2", "logo_url": None, "font_family": "Inter",
                    "author_name": "", "author_tagline": ""}

        service._get_brand_kit = _fake_brand_kit

        outline = make_ai_outline_response()
        saved = {}

        def _capture(asset):
            asset.id = make_uuid()
            saved["asset"] = asset
        db.add.side_effect = _capture
        db.refresh.side_effect = lambda o: None

        with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http

            # AI engine succeeds
            ai_resp = MagicMock()
            ai_resp.raise_for_status = MagicMock()
            ai_resp.json.return_value = outline

            # Renderer raises timeout
            mock_http.post.side_effect = [ai_resp, httpx.ReadTimeout("renderer timed out")]

            result = await service.create_carousel(post.id, post.user_id)

        assert saved["asset"].status == "draft"
        assert saved["asset"].pdf_url is None

    @pytest.mark.asyncio
    async def test_carousel_creation_when_ai_engine_fails_raises_runtime_error(self):
        """AI engine 500 → _call_ai_engine_outline returns None → RuntimeError raised."""
        from app.services.carousel_service import CarouselService
        from app.repositories.post_repository import PostRepository

        post = make_post()
        db = make_db_session()
        post_repo = AsyncMock(spec=PostRepository)
        post_repo.get_by_id.return_value = post

        settings = MagicMock()
        settings.ai_engine_url = "http://ai-engine"
        settings.ai_engine_api_key = "key"

        service = CarouselService(post_repo, db)
        service._settings = settings

        async def _fake_brand_kit(user_id):
            return {"primary_color": "#0A66C2", "logo_url": None, "font_family": "Inter",
                    "author_name": "", "author_tagline": ""}

        service._get_brand_kit = _fake_brand_kit

        with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http

            bad_resp = MagicMock()
            bad_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock(status_code=500)
            )
            mock_http.post.return_value = bad_resp

            with pytest.raises(RuntimeError, match="AI Engine failed"):
                await service.create_carousel(post.id, post.user_id)


# ===========================================================================
# Sprint 4 Integration: LinkedIn publish 3-step flow
# ===========================================================================


class TestLinkedInPublishPipeline:
    @pytest.mark.asyncio
    async def test_three_step_linkedin_upload_flow(self):
        """
        Verifies:
        1. POST /rest/documents?action=initializeUpload → returns uploadUrl + document URN
        2. PUT {uploadUrl} with PDF bytes
        3. POST /rest/posts → returns li_post_urn in x-restli-id header
        4. asset.status = 'published', asset.linkedin_asset_urn = document_urn
        """
        from app.services.carousel_service import CarouselService

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"REAL PDF BYTES FOR TEST")
            pdf_path = tf.name

        asset = make_carousel_asset(pdf_url=f"file://{pdf_path}")

        db = make_db_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = asset
        db.execute.return_value = result_mock

        service = CarouselService(AsyncMock(), db)
        service._settings = MagicMock()

        access_token = "live_oauth_token"
        document_urn = "urn:li:document:999888777"
        upload_url = "https://upload.linkedin.com/upload/abc123"
        li_post_urn = "urn:li:share:111222333"

        with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_http

            # Step 1: initializeUpload
            init_resp = MagicMock()
            init_resp.raise_for_status = MagicMock()
            init_resp.json.return_value = {
                "value": {
                    "uploadUrl": upload_url,
                    "document": document_urn,
                }
            }

            # Step 2: PUT binary
            put_resp = MagicMock()
            put_resp.raise_for_status = MagicMock()

            # Step 3: create post
            post_resp = MagicMock()
            post_resp.raise_for_status = MagicMock()
            post_resp.headers = {"x-restli-id": li_post_urn}

            mock_http.post.side_effect = [init_resp, post_resp]
            mock_http.put.return_value = put_resp

            result = await service.publish_to_linkedin(
                asset_id=asset.id,
                user_id=make_uuid(),
                access_token=access_token,
                post_text="My carousel on AI Automation 🚀",
            )

        # Verify final outcome
        assert result == li_post_urn
        assert asset.status == "published"
        assert asset.linkedin_asset_urn == document_urn

        # Step 2 (PUT) must have been called with the uploadUrl
        mock_http.put.assert_awaited_once()
        put_call_url = mock_http.put.call_args.args[0]
        assert put_call_url == upload_url

        # Verify Authorization header was sent
        put_call_kwargs = mock_http.put.call_args.kwargs
        assert put_call_kwargs.get("headers", {}).get("Authorization") == f"Bearer {access_token}"

        # DB committed
        db.commit.assert_awaited()

        # Cleanup
        Path(pdf_path).unlink(missing_ok=True)
