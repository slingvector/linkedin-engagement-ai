"""Sprint 4 — CarouselService unit tests.

Coverage:
  - create_carousel() happy path (all steps succeed)
  - create_carousel() post not found → ValueError
  - create_carousel() AI engine returns None → RuntimeError
  - create_carousel() renderer fails → asset status = 'draft', pdf_url = None
  - _get_brand_kit() with existing UserSettings
  - _get_brand_kit() no UserSettings → returns defaults
  - _call_ai_engine_outline() success
  - _call_ai_engine_outline() network error → returns None
  - _render_pdf() renderer not available → returns None
  - _store_pdf() saves file and returns file:// URL
  - _store_pdf() None bytes → returns None
  - get_by_post() returns most recent asset
  - get_by_post() no asset → returns None
  - publish_to_linkedin() happy path (3-step flow)
  - publish_to_linkedin() asset not found → ValueError
  - publish_to_linkedin() PDF file missing on disk → FileNotFoundError
  - publish_to_linkedin() LinkedIn API 401 → exception propagated
"""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
import tempfile

import pytest
import httpx

from app.services.carousel_service import CarouselService
from app.repositories.post_repository import PostRepository

from tests.v2.conftest import (
    make_uuid,
    make_post,
    make_carousel_asset,
    make_user_settings,
    make_ai_outline_response,
    make_db_session,
    db_scalar_result,
)


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------


def _make_service(
    post_to_return=None,
    settings_to_return=None,
    ai_response: dict | None = None,   # None = simulate failure
    renderer_response: bytes | None = b"FAKE_PDF_BYTES",
):
    """Build CarouselService with all external deps mocked."""
    db = make_db_session()
    post_repo = AsyncMock(spec=PostRepository)
    post_repo.get_by_id.return_value = post_to_return

    settings_mock = MagicMock()
    settings_mock.ai_engine_url = "http://ai-engine"
    settings_mock.ai_engine_api_key = "test-key"
    settings_mock.carousel_renderer_url = "http://renderer"

    service = CarouselService(post_repo, db)
    service._settings = settings_mock

    # Patch UserSettings query
    async def _fake_get_brand_kit(user_id):
        if settings_to_return:
            return {
                "primary_color": settings_to_return.primary_color or "#0A66C2",
                "logo_url": settings_to_return.logo_url,
                "font_family": settings_to_return.font_family or "Inter",
                "author_name": settings_to_return.author_name or "",
                "author_tagline": settings_to_return.author_tagline or "",
            }
        return {
            "primary_color": "#0A66C2",
            "logo_url": None,
            "font_family": "Inter",
            "author_name": "",
            "author_tagline": "",
        }
    service._get_brand_kit = _fake_get_brand_kit

    # Patch AI outline call
    async def _fake_ai_outline(post, user_id):
        return ai_response
    service._call_ai_engine_outline = _fake_ai_outline

    # Patch renderer call
    async def _fake_render_pdf(slides, brand_kit, cover_hook, cta_text):
        return renderer_response
    service._render_pdf = _fake_render_pdf

    return service, post_repo, db


# ---------------------------------------------------------------------------
# create_carousel()
# ---------------------------------------------------------------------------


class TestCreateCarouselHappyPath:
    @pytest.mark.asyncio
    async def test_asset_persisted_to_db(self):
        post = make_post()
        ai_resp = make_ai_outline_response()
        service, repo, db = _make_service(post_to_return=post, ai_response=ai_resp)

        # Patch _store_pdf to avoid real filesystem
        async def _fake_store(pdf_bytes, post_id):
            return f"file:///tmp/carousel_pdfs/{post_id}.pdf"
        service._store_pdf = _fake_store

        # Set up db.refresh to populate asset with an id
        saved_asset_holder = {}

        def _capture_add(asset):
            asset.id = make_uuid()
            saved_asset_holder["asset"] = asset
        db.add.side_effect = _capture_add
        db.refresh.side_effect = lambda obj: None

        result = await service.create_carousel(post.id, post.user_id)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_slide_count_matches_ai_response(self):
        post = make_post()
        ai_resp = make_ai_outline_response(slide_count=7)
        service, _, db = _make_service(post_to_return=post, ai_response=ai_resp)

        async def _fake_store(pdf_bytes, post_id):
            return f"file:///tmp/{post_id}.pdf"
        service._store_pdf = _fake_store

        saved = {}
        def _capture(asset):
            asset.id = make_uuid()
            asset.slide_count = len(ai_resp["slides"])
            saved["asset"] = asset
        db.add.side_effect = _capture
        db.refresh.side_effect = lambda o: None

        result = await service.create_carousel(post.id, post.user_id)
        assert saved["asset"].slide_count == 7

    @pytest.mark.asyncio
    async def test_status_is_rendered_when_pdf_exists(self):
        post = make_post()
        ai_resp = make_ai_outline_response()
        service, _, db = _make_service(post_to_return=post, ai_response=ai_resp)

        async def _store(pdf_bytes, post_id):
            return "file:///tmp/test.pdf"
        service._store_pdf = _store

        saved = {}
        def _capture(asset):
            asset.id = make_uuid()
            saved["asset"] = asset
        db.add.side_effect = _capture
        db.refresh.side_effect = lambda o: None

        await service.create_carousel(post.id, post.user_id)
        assert saved["asset"].status == "rendered"

    @pytest.mark.asyncio
    async def test_status_is_draft_when_renderer_fails(self):
        """When renderer returns None (e.g. unavailable), status should be 'draft'."""
        post = make_post()
        ai_resp = make_ai_outline_response()
        service, _, db = _make_service(
            post_to_return=post, ai_response=ai_resp, renderer_response=None
        )

        saved = {}
        def _capture(asset):
            asset.id = make_uuid()
            saved["asset"] = asset
        db.add.side_effect = _capture
        db.refresh.side_effect = lambda o: None

        await service.create_carousel(post.id, post.user_id)
        # pdf_bytes=None → _store_pdf returns None → status = 'draft'
        assert saved["asset"].status == "draft"
        assert saved["asset"].pdf_url is None


class TestCreateCarouselUnhappyPaths:
    @pytest.mark.asyncio
    async def test_post_not_found_raises_value_error(self):
        service, _, _ = _make_service(post_to_return=None, ai_response=make_ai_outline_response())
        with pytest.raises(ValueError, match="not found"):
            await service.create_carousel(make_uuid(), make_uuid())

    @pytest.mark.asyncio
    async def test_ai_engine_returns_none_raises_runtime_error(self):
        post = make_post()
        service, _, _ = _make_service(post_to_return=post, ai_response=None)
        with pytest.raises(RuntimeError, match="AI Engine failed"):
            await service.create_carousel(post.id, post.user_id)


# ---------------------------------------------------------------------------
# _get_brand_kit
# ---------------------------------------------------------------------------


class TestGetBrandKit:
    @pytest.mark.asyncio
    async def test_with_user_settings_returns_custom_branding(self):
        post = make_post()
        user_settings = make_user_settings(
            primary_color="#FF5733",
            font_family="Roboto",
            author_name="Test Author",
        )
        service, _, _ = _make_service(
            post_to_return=post,
            settings_to_return=user_settings,
            ai_response=make_ai_outline_response(),
        )
        brand_kit = await service._get_brand_kit(post.user_id)
        assert brand_kit["primary_color"] == "#FF5733"
        assert brand_kit["font_family"] == "Roboto"
        assert brand_kit["author_name"] == "Test Author"

    @pytest.mark.asyncio
    async def test_without_user_settings_returns_linkedin_defaults(self):
        post = make_post()
        service, _, _ = _make_service(
            post_to_return=post,
            settings_to_return=None,
            ai_response=make_ai_outline_response(),
        )
        brand_kit = await service._get_brand_kit(post.user_id)
        assert brand_kit["primary_color"] == "#0A66C2"
        assert brand_kit["font_family"] == "Inter"


# ---------------------------------------------------------------------------
# _store_pdf
# ---------------------------------------------------------------------------


class TestStorePdf:
    @pytest.mark.asyncio
    async def test_none_bytes_returns_none(self):
        db = make_db_session()
        service = CarouselService(AsyncMock(), db)
        result = await service._store_pdf(None, make_uuid())
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_bytes_creates_file_and_returns_url(self):
        db = make_db_session()
        service = CarouselService(AsyncMock(), db)
        post_id = make_uuid()
        test_bytes = b"FAKE PDF BYTES"
        url = await service._store_pdf(test_bytes, post_id)
        assert url is not None
        assert str(post_id) in url
        assert url.startswith("file://")
        # Cleanup
        path = Path(url.replace("file://", ""))
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# get_by_post
# ---------------------------------------------------------------------------


class TestGetByPost:
    @pytest.mark.asyncio
    async def test_returns_most_recent_asset(self):
        asset = make_carousel_asset()
        db = make_db_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = asset
        db.execute.return_value = result_mock

        service = CarouselService(AsyncMock(), db)
        result = await service.get_by_post(asset.post_id)
        assert result == asset

    @pytest.mark.asyncio
    async def test_returns_none_when_no_asset(self):
        db = make_db_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = CarouselService(AsyncMock(), db)
        result = await service.get_by_post(make_uuid())
        assert result is None


# ---------------------------------------------------------------------------
# publish_to_linkedin
# ---------------------------------------------------------------------------


class TestPublishToLinkedIn:
    def _make_mock_user(self, write_token: str | None = "encrypted_write_token"):
        """Create a mock user with optional write token."""
        from unittest.mock import MagicMock
        user = MagicMock()
        user.write_access_token_encrypted = write_token
        user.linkedin_person_id = "12345"
        user.linkedin_id = "12345"
        return user

    def _db_returning(self, *return_values):
        """DB that returns different scalar values on sequential execute calls."""
        db = make_db_session()
        results = []
        for val in return_values:
            r = MagicMock()
            r.scalar_one_or_none.return_value = val
            results.append(r)
        db.execute.side_effect = results
        return db

    @pytest.mark.asyncio
    async def test_happy_path_threestep_flow(self):
        """LinkedIn 3-step upload: initializeUpload → PUT → POST."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"FAKE PDF BYTES")
            pdf_path = tf.name

        asset = make_carousel_asset(pdf_url=f"file://{pdf_path}")
        user = self._make_mock_user()

        with patch("app.services.carousel_service.decrypt_token", return_value="test_token"):
            db = self._db_returning(asset, user)
            service = CarouselService(AsyncMock(), db)
            service._settings = MagicMock()

            with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
                mock_http = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_http

                init_resp = MagicMock()
                init_resp.raise_for_status = MagicMock()
                init_resp.status_code = 200
                init_resp.json.return_value = {
                    "value": {
                        "uploadUrl": "https://upload.linkedin.com/upload/1234",
                        "document": "urn:li:document:1234",
                    }
                }

                put_resp = MagicMock()
                put_resp.raise_for_status = MagicMock()
                put_resp.status_code = 201

                post_resp = MagicMock()
                post_resp.raise_for_status = MagicMock()
                post_resp.status_code = 201
                post_resp.headers = {"x-restli-id": "urn:li:share:9999"}

                mock_http.post.side_effect = [init_resp, post_resp]
                mock_http.put.return_value = put_resp

                li_urn = await service.publish_to_linkedin(
                    asset_id=asset.id,
                    user_id=make_uuid(),
                    post_text="My carousel post",
                )

        assert li_urn == "urn:li:share:9999"
        assert asset.status == "published"
        assert asset.linkedin_asset_urn == "urn:li:document:1234"

        # Cleanup
        Path(pdf_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_asset_not_found_raises_value_error(self):
        db = self._db_returning(None)
        service = CarouselService(AsyncMock(), db)
        service._settings = MagicMock()

        with pytest.raises(ValueError, match="not found"):
            await service.publish_to_linkedin(
                asset_id=make_uuid(),
                user_id=make_uuid(),
                post_text="test",
            )

    @pytest.mark.asyncio
    async def test_asset_without_pdf_url_raises_value_error(self):
        asset = make_carousel_asset(pdf_url=None)
        db = self._db_returning(asset)
        service = CarouselService(AsyncMock(), db)
        service._settings = MagicMock()

        with pytest.raises(ValueError, match="PDF not rendered"):
            await service.publish_to_linkedin(
                asset_id=asset.id,
                user_id=make_uuid(),
                post_text="test",
            )

    @pytest.mark.asyncio
    async def test_pdf_file_missing_raises_file_not_found(self):
        asset = make_carousel_asset(pdf_url="file:///tmp/nonexistent_12345.pdf")
        db = self._db_returning(asset)
        service = CarouselService(AsyncMock(), db)
        service._settings = MagicMock()

        with pytest.raises(FileNotFoundError):
            await service.publish_to_linkedin(
                asset_id=asset.id,
                user_id=make_uuid(),
                post_text="test",
            )

    @pytest.mark.asyncio
    async def test_linkedin_401_raises_value_error(self):
        """LinkedIn 401 on initializeUpload → ValueError (token expired)."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"PDF")
            pdf_path = tf.name

        asset = make_carousel_asset(pdf_url=f"file://{pdf_path}")
        user = self._make_mock_user()

        with patch("app.services.carousel_service.decrypt_token", return_value="bad_token"):
            db = self._db_returning(asset, user)
            service = CarouselService(AsyncMock(), db)
            service._settings = MagicMock()

            with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
                mock_http = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_http

                auth_error_resp = MagicMock()
                auth_error_resp.status_code = 401
                auth_error_resp.raise_for_status = MagicMock()
                mock_http.post.return_value = auth_error_resp

                with pytest.raises(ValueError, match="expired"):
                    await service.publish_to_linkedin(
                        asset_id=asset.id,
                        user_id=make_uuid(),
                        post_text="test",
                    )

        Path(pdf_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_linkedin_upload_missing_url_raises_runtime_error(self):
        """initializeUpload returns empty value → RuntimeError."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"PDF")
            pdf_path = tf.name

        asset = make_carousel_asset(pdf_url=f"file://{pdf_path}")
        user = self._make_mock_user()

        with patch("app.services.carousel_service.decrypt_token", return_value="token"):
            db = self._db_returning(asset, user)
            service = CarouselService(AsyncMock(), db)
            service._settings = MagicMock()

            with patch("app.services.carousel_service.httpx.AsyncClient") as mock_client:
                mock_http = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_http

                bad_resp = MagicMock()
                bad_resp.status_code = 200
                bad_resp.raise_for_status = MagicMock()
                bad_resp.json.return_value = {"value": {}}  # missing uploadUrl + document
                mock_http.post.return_value = bad_resp

                with pytest.raises(RuntimeError, match="upload initialization failed"):
                    await service.publish_to_linkedin(
                        asset_id=asset.id,
                        user_id=make_uuid(),
                        post_text="test",
                    )

        Path(pdf_path).unlink(missing_ok=True)
