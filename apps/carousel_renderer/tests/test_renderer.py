"""Carousel Renderer microservice — comprehensive tests.

Coverage:
  GET /health
    ✓ 200 — returns {status, service, weasyprint}

  POST /render
    ✓ 200 — valid 7-slide request → returns pdf_base64 + page_count
    ✓ 200 — valid 1-slide request (edge: single slide)
    ✓ 400 — empty slides array
    ✓ 422 — missing required field (slides)
    ✓ 200 — brand_kit with custom primary_color and font_family
    ✓ 200 — brand_kit missing → uses defaults
    ✓ 200 — slide missing optional fields (visual_suggestion empty)
    ✓ pdf_base64 is valid base64 string
    ✓ page_count matches len(slides)
    ✓ Renderer fallback (WeasyPrint unavailable) → still returns valid base64
    ✓ cover_hook in request (exercises Jinja template is_cover logic)
    ✓ cta_text in request (exercises Jinja template is_cta logic)
    ✓ 500 — rendering engine raises unexpected exception
"""

from __future__ import annotations

import base64
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    import sys
    import os
    renderer_path = os.path.join(
        os.path.dirname(__file__), "..", ".."
    )
    sys.path.insert(0, renderer_path)
    import importlib
    import main as renderer_main
    importlib.reload(renderer_main)
    return renderer_main.app


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_slide(n: int = 1) -> dict:
    return {
        "slide_number": n,
        "headline": f"Headline for slide {n}",
        "body": f"Body content for slide {n}. Short and punchy.",
        "visual_suggestion": "Abstract gradient background",
    }


def _make_slides(count: int = 7) -> list[dict]:
    return [_make_slide(i) for i in range(1, count + 1)]


def _make_brand_kit(
    primary_color: str = "#0A66C2",
    font_family: str = "Inter",
    author_name: str = "Test User",
    author_tagline: str = "LinkedIn Guru",
) -> dict:
    return {
        "primary_color": primary_color,
        "logo_url": None,
        "font_family": font_family,
        "author_name": author_name,
        "author_tagline": author_tagline,
    }


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_200_health_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "carousel_renderer"
        assert "weasyprint" in body

    @pytest.mark.asyncio
    async def test_weasyprint_field_is_bool(self, client):
        resp = await client.get("/health")
        assert isinstance(resp.json()["weasyprint"], bool)


# ---------------------------------------------------------------------------
# Render endpoint — happy paths
# ---------------------------------------------------------------------------


class TestRenderEndpointHappyPath:
    @pytest.mark.asyncio
    async def test_200_seven_slides(self, client):
        slides = _make_slides(7)
        resp = await client.post(
            "/render",
            json={
                "slides": slides,
                "brand_kit": _make_brand_kit(),
                "cover_hook": "The one framework that changed my business",
                "cta_text": "Follow for more →",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pdf_base64_present_and_decodable(self, client):
        slides = _make_slides(3)
        resp = await client.post(
            "/render",
            json={"slides": slides, "brand_kit": _make_brand_kit()},
        )
        assert resp.status_code == 200
        b64 = resp.json()["pdf_base64"]
        assert isinstance(b64, str)
        # Should not raise
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    @pytest.mark.asyncio
    async def test_page_count_matches_slides(self, client):
        count = 5
        slides = _make_slides(count)
        resp = await client.post(
            "/render",
            json={"slides": slides, "brand_kit": _make_brand_kit()},
        )
        assert resp.json()["page_count"] == count

    @pytest.mark.asyncio
    async def test_single_slide(self, client):
        resp = await client.post(
            "/render",
            json={"slides": [_make_slide(1)], "brand_kit": _make_brand_kit()},
        )
        assert resp.status_code == 200
        assert resp.json()["page_count"] == 1

    @pytest.mark.asyncio
    async def test_custom_brand_kit_accepted(self, client):
        resp = await client.post(
            "/render",
            json={
                "slides": _make_slides(2),
                "brand_kit": {
                    "primary_color": "#FF5733",
                    "logo_url": None,
                    "font_family": "Roboto",
                    "author_name": "Custom Author",
                    "author_tagline": "Custom Tagline",
                },
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_brand_kit_uses_defaults(self, client):
        resp = await client.post(
            "/render",
            json={"slides": _make_slides(2), "brand_kit": {}},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_brand_kit_uses_defaults(self, client):
        resp = await client.post(
            "/render",
            json={"slides": _make_slides(2)},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cover_hook_and_cta_text_accepted(self, client):
        resp = await client.post(
            "/render",
            json={
                "slides": _make_slides(7),
                "brand_kit": _make_brand_kit(),
                "cover_hook": "Custom cover hook text here",
                "cta_text": "Subscribe now →",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_slide_with_empty_visual_suggestion(self, client):
        slide = _make_slide(1)
        slide["visual_suggestion"] = ""
        resp = await client.post(
            "/render",
            json={"slides": [slide], "brand_kit": _make_brand_kit()},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Render endpoint — unhappy paths
# ---------------------------------------------------------------------------


class TestRenderEndpointUnhappyPaths:
    @pytest.mark.asyncio
    async def test_400_empty_slides_array(self, client):
        resp = await client.post(
            "/render",
            json={"slides": [], "brand_kit": _make_brand_kit()},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_422_missing_slides_field(self, client):
        resp = await client.post(
            "/render",
            json={"brand_kit": _make_brand_kit()},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_422_slide_missing_headline(self, client):
        """Headline is a required field on Slide model."""
        resp = await client.post(
            "/render",
            json={
                "slides": [
                    {
                        "slide_number": 1,
                        # "headline" missing
                        "body": "body",
                        "visual_suggestion": "img",
                    }
                ],
                "brand_kit": _make_brand_kit(),
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_500_renderer_engine_throws_exception(self, client):
        """Simulate an internal rendering error."""
        with patch("main._render_slides_html", side_effect=Exception("Template error")):
            resp = await client.post(
                "/render",
                json={"slides": _make_slides(2), "brand_kit": _make_brand_kit()},
            )
        assert resp.status_code == 500
        assert "Rendering failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# WeasyPrint fallback tests
# ---------------------------------------------------------------------------


class TestWeasyPrintFallback:
    @pytest.mark.asyncio
    async def test_fallback_to_html_when_weasyprint_unavailable(self, client):
        """When WeasyPrint is not available, renderer falls back to HTML bytes."""
        with patch("main.WEASYPRINT_AVAILABLE", False):
            resp = await client.post(
                "/render",
                json={"slides": _make_slides(3), "brand_kit": _make_brand_kit()},
            )
        assert resp.status_code == 200
        b64 = resp.json()["pdf_base64"]
        decoded = base64.b64decode(b64).decode("utf-8")
        # In fallback mode, the "PDF" is actually the rendered HTML
        assert len(decoded) > 0

    @pytest.mark.asyncio
    async def test_fallback_page_count_still_correct(self, client):
        with patch("main.WEASYPRINT_AVAILABLE", False):
            count = 4
            resp = await client.post(
                "/render",
                json={"slides": _make_slides(count), "brand_kit": _make_brand_kit()},
            )
        assert resp.json()["page_count"] == count


# ---------------------------------------------------------------------------
# _render_slides_html unit tests (pure function)
# ---------------------------------------------------------------------------


class TestRenderSlidesHtmlUnit:
    def test_html_contains_headlines(self):
        from main import _render_slides_html, RenderRequest, Slide, BrandKit

        slides = [
            Slide(
                slide_number=1,
                headline="My Custom Headline",
                body="Body",
                visual_suggestion="img",
            )
        ]
        request = RenderRequest(
            slides=slides,
            brand_kit=BrandKit(),
        )
        html = _render_slides_html(request)
        assert "My Custom Headline" in html

    def test_html_is_str(self):
        from main import _render_slides_html, RenderRequest, Slide, BrandKit

        slides = [Slide(slide_number=1, headline="H", body="B", visual_suggestion="V")]
        request = RenderRequest(slides=slides, brand_kit=BrandKit())
        result = _render_slides_html(request)
        assert isinstance(result, str)

    def test_multiple_slides_all_rendered(self):
        from main import _render_slides_html, RenderRequest, Slide, BrandKit

        slides = [
            Slide(slide_number=i, headline=f"Slide {i}", body="b", visual_suggestion="v")
            for i in range(1, 4)
        ]
        request = RenderRequest(slides=slides, brand_kit=BrandKit())
        html = _render_slides_html(request)
        for i in range(1, 4):
            assert f"Slide {i}" in html
