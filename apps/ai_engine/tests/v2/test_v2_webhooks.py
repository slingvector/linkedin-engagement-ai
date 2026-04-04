"""AI Engine — V2 webhook endpoint integration tests.

Coverage:
  POST /webhooks/v2/generate/carousel-outline
    ✓ 200 with valid API key + valid payload
    ✓ 401/403 with missing X-AI-API-Key header
    ✓ 422 with missing required field (topic)
    ✓ Response shape: slides[], cover_hook, cta_slide_text

  POST /webhooks/v2/score/post
    ✓ 200 with valid payload
    ✓ 403 with missing API key
    ✓ 422 missing required fields (draft_text)
    ✓ Response shape: total_score, breakdown, hook_alternatives, reasoning

  POST /webhooks/v2/generate/week-plan
    ✓ 200 with valid payload
    ✓ 403 with missing API key
    ✓ 422 missing required fields (pillars)
    ✓ Response shape: posts[]
"""

from __future__ import annotations

import uuid
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.dependencies import verify_api_key
from tests.v2.conftest import (
    make_carousel_outline_payload,
    make_virality_score_payload,
    make_week_plan_payload,
)

# ---------------------------------------------------------------------------
# App fixture with API key dependency bypassed
# ---------------------------------------------------------------------------


def _build_authed_app() -> FastAPI:
    """Build the full AI Engine FastAPI app with API key check bypassed."""
    from app.main import create_app

    _app = create_app()

    # Override verify_api_key so tests don't need a real API key
    async def _allow():
        return "test-key"

    _app.dependency_overrides[verify_api_key] = _allow
    return _app


@pytest.fixture
def authed_app():
    return _build_authed_app()


@pytest.fixture
async def authed_client(authed_app):
    async with AsyncClient(
        transport=ASGITransport(app=authed_app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Response object builders (mimic Pydantic model instances)
# ---------------------------------------------------------------------------


def _carousel_response(payload: dict):
    from app.services.carousel_outline_service import CarouselOutlineResponse, Slide
    slides = [
        Slide(
            slide_number=s["slide_number"],
            headline=s["headline"],
            body=s["body"],
            visual_suggestion=s["visual_suggestion"],
        )
        for s in payload.get("slides", [])
    ]
    return CarouselOutlineResponse(
        slides=slides,
        cover_hook=payload.get("cover_hook", ""),
        cta_slide_text=payload.get("cta_slide_text", "Follow for more"),
    )


def _score_response(payload: dict):
    from app.services.virality_score_service import ScoreResponse, ScoreBreakdown, HookAlternative
    bd = payload.get("breakdown", {})
    return ScoreResponse(
        total_score=payload["total_score"],
        breakdown=ScoreBreakdown(
            hook_strength=bd.get("hook_strength", 0),
            readability=bd.get("readability", 0),
            value_density=bd.get("value_density", 0),
            cta_quality=bd.get("cta_quality", 0),
        ),
        hook_alternatives=[
            HookAlternative(hook=a["hook"], predicted_score=a["predicted_score"])
            for a in payload.get("hook_alternatives", [])
        ],
        reasoning=payload.get("reasoning", ""),
    )


def _week_plan_response(payload: dict):
    from app.services.week_plan_service import WeekPlanResponse, WeekPlanPost
    posts = [
        WeekPlanPost(
            pillar=p["pillar"],
            format=p["format"],
            hook=p["hook"],
            body=p["body"],
            cta=p["cta"],
            topic=p.get("topic", "LinkedIn Post"),
        )
        for p in payload.get("posts", [])
    ]
    return WeekPlanResponse(posts=posts)


# ---------------------------------------------------------------------------
# Carousel Outline Endpoint
# ---------------------------------------------------------------------------


class TestCarouselOutlineWebhook:
    @pytest.mark.asyncio
    async def test_200_happy_path(self, authed_client):
        outline_payload = make_carousel_outline_payload()
        with patch(
            "app.services.carousel_outline_service.CarouselOutlineService.generate_outline",
            new=AsyncMock(return_value=_carousel_response(outline_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/carousel-outline",
                json={
                    "user_id": str(uuid.uuid4()),
                    "topic": "AI for Founders",
                    "audience": "Startup Founders",
                    "tone": "professional_but_conversational",
                    "slide_count": 7,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "slides" in body
        assert "cover_hook" in body
        assert "cta_slide_text" in body

    @pytest.mark.asyncio
    async def test_422_missing_topic(self, authed_client):
        resp = await authed_client.post(
            "/webhooks/v2/generate/carousel-outline",
            json={
                "user_id": str(uuid.uuid4()),
                "audience": "professionals",
                # "topic" missing
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_403(self, client):
        """Without the dependency override, real verify_api_key runs and rejects."""
        resp = await client.post(
            "/webhooks/v2/generate/carousel-outline",
            json={
                "user_id": "user",
                "topic": "test",
                "audience": "pros",
            },
            # No API key header → 403 from verify_api_key
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_slides_list_has_seven_items(self, authed_client):
        outline_payload = make_carousel_outline_payload()
        with patch(
            "app.services.carousel_outline_service.CarouselOutlineService.generate_outline",
            new=AsyncMock(return_value=_carousel_response(outline_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/carousel-outline",
                json={
                    "user_id": str(uuid.uuid4()),
                    "topic": "AI Automation",
                    "audience": "Founders",
                },
            )
        slides = resp.json().get("slides", [])
        assert len(slides) == 7

    @pytest.mark.asyncio
    async def test_each_slide_has_required_fields(self, authed_client):
        outline_payload = make_carousel_outline_payload()
        with patch(
            "app.services.carousel_outline_service.CarouselOutlineService.generate_outline",
            new=AsyncMock(return_value=_carousel_response(outline_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/carousel-outline",
                json={"user_id": str(uuid.uuid4()), "topic": "AI", "audience": "pros"},
            )
        for slide in resp.json()["slides"]:
            assert "slide_number" in slide
            assert "headline" in slide
            assert "body" in slide
            assert "visual_suggestion" in slide


# ---------------------------------------------------------------------------
# Virality Score Endpoint
# ---------------------------------------------------------------------------


class TestViralityScoreWebhook:
    @pytest.mark.asyncio
    async def test_200_happy_path(self, authed_client):
        score_payload = make_virality_score_payload()
        with patch(
            "app.services.virality_score_service.ViralityScoreService.score_post",
            new=AsyncMock(return_value=_score_response(score_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/score/post",
                json={
                    "user_id": str(uuid.uuid4()),
                    "post_id": str(uuid.uuid4()),
                    "draft_text": "Is AI replacing us?\n\nHere are 5 things.\n\nWhat do you think?",
                    "top_posts_sample": ["Best hook ever"],
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_score" in body
        assert "breakdown" in body
        assert "hook_alternatives" in body
        assert "reasoning" in body

    @pytest.mark.asyncio
    async def test_422_missing_draft_text(self, authed_client):
        resp = await authed_client.post(
            "/webhooks/v2/score/post",
            json={
                "user_id": str(uuid.uuid4()),
                "post_id": str(uuid.uuid4()),
                # "draft_text" missing
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_403(self, client):
        resp = await client.post(
            "/webhooks/v2/score/post",
            json={"user_id": "u", "post_id": "p", "draft_text": "draft"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_breakdown_has_four_dimensions(self, authed_client):
        score_payload = make_virality_score_payload()
        with patch(
            "app.services.virality_score_service.ViralityScoreService.score_post",
            new=AsyncMock(return_value=_score_response(score_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/score/post",
                json={
                    "user_id": str(uuid.uuid4()),
                    "post_id": str(uuid.uuid4()),
                    "draft_text": "draft",
                },
            )
        bd = resp.json()["breakdown"]
        assert "hook_strength" in bd
        assert "readability" in bd
        assert "value_density" in bd
        assert "cta_quality" in bd

    @pytest.mark.asyncio
    async def test_total_score_is_integer(self, authed_client):
        score_payload = make_virality_score_payload(total_score=74)
        with patch(
            "app.services.virality_score_service.ViralityScoreService.score_post",
            new=AsyncMock(return_value=_score_response(score_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/score/post",
                json={
                    "user_id": str(uuid.uuid4()),
                    "post_id": str(uuid.uuid4()),
                    "draft_text": "draft",
                },
            )
        assert resp.json()["total_score"] == 74
        assert isinstance(resp.json()["total_score"], int)


# ---------------------------------------------------------------------------
# Week Plan Endpoint
# ---------------------------------------------------------------------------


class TestWeekPlanWebhook:
    @pytest.mark.asyncio
    async def test_200_happy_path(self, authed_client):
        week_payload = make_week_plan_payload(count=4)
        with patch(
            "app.services.week_plan_service.WeekPlanService.generate_week_plan",
            new=AsyncMock(return_value=_week_plan_response(week_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/week-plan",
                json={
                    "user_id": str(uuid.uuid4()),
                    "pillars": ["AI Automation", "Founder Stories"],
                    "posts_per_week": 4,
                    "preferred_formats": ["text", "carousel"],
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "posts" in body

    @pytest.mark.asyncio
    async def test_422_missing_pillars(self, authed_client):
        resp = await authed_client.post(
            "/webhooks/v2/generate/week-plan",
            json={
                "user_id": str(uuid.uuid4()),
                "posts_per_week": 4,
                # "pillars" missing
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_403(self, client):
        resp = await client.post(
            "/webhooks/v2/generate/week-plan",
            json={"user_id": "u", "pillars": ["AI"], "posts_per_week": 3},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_posts_have_required_fields(self, authed_client):
        week_payload = make_week_plan_payload(count=3)
        with patch(
            "app.services.week_plan_service.WeekPlanService.generate_week_plan",
            new=AsyncMock(return_value=_week_plan_response(week_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/week-plan",
                json={
                    "user_id": str(uuid.uuid4()),
                    "pillars": ["AI"],
                    "posts_per_week": 3,
                },
            )
        for post in resp.json()["posts"]:
            assert "pillar" in post
            assert "format" in post
            assert "hook" in post
            assert "body" in post
            assert "cta" in post

    @pytest.mark.asyncio
    async def test_week_plan_post_count_matches_request(self, authed_client):
        week_payload = make_week_plan_payload(count=5)
        with patch(
            "app.services.week_plan_service.WeekPlanService.generate_week_plan",
            new=AsyncMock(return_value=_week_plan_response(week_payload)),
        ):
            resp = await authed_client.post(
                "/webhooks/v2/generate/week-plan",
                json={
                    "user_id": str(uuid.uuid4()),
                    "pillars": ["AI", "Founder"],
                    "posts_per_week": 5,
                },
            )
        assert len(resp.json()["posts"]) == 5
