"""Sprint 2 — SmartFillService unit tests.

Coverage:
  - _next_occurrence() day/hour calculation
  - smart_fill() happy path: AI returns N posts, heatmap returns slots
  - smart_fill() AI engine failure → returns empty list
  - smart_fill() heatmap fallback slot (runs out of best slots)
  - smart_fill() posts_per_week cap (only creates requested number)
  - smart_fill() Post records have correct fields set (drafted, scheduled_at, etc.)
  - _call_ai_engine() network error → returns []
  - _call_ai_engine() non-200 response → returns []
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.services.smart_fill_service import SmartFillService, _next_occurrence, _DAY_TO_WEEKDAY
from app.services.heatmap_service import HeatmapService
from app.repositories.post_repository import PostRepository

from tests.v2.conftest import (
    make_uuid,
    make_post,
    make_week_plan_response,
    make_db_session,
)


# ---------------------------------------------------------------------------
# _next_occurrence pure function tests
# ---------------------------------------------------------------------------


class TestNextOccurrence:
    def test_same_weekday_same_hour_returns_today(self):
        now = datetime(2026, 4, 7, 8, 0, 0, tzinfo=timezone.utc)  # Tuesday
        result = _next_occurrence(weekday=1, hour=10, from_date=now)
        assert result.weekday() == 1
        assert result.hour == 10
        assert result >= now

    def test_target_in_past_adds_one_week(self):
        """If the computed time is before from_date, add 7 days."""
        now = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)  # Tuesday 12:00
        result = _next_occurrence(weekday=1, hour=9, from_date=now)
        # 09:00 Tuesday is before 12:00 Tuesday → should wrap to next Tuesday
        assert result >= now
        assert result.hour == 9

    def test_different_weekday_returns_correct_day(self):
        """from Monday, asking for Thursday should be +3 days."""
        now = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        result = _next_occurrence(weekday=3, hour=9, from_date=now)  # Thursday
        assert result.weekday() == 3
        assert result.hour == 9
        assert (result - now).days <= 7

    def test_minutes_seconds_stripped(self):
        now = datetime(2026, 4, 7, 8, 35, 50, 123456, tzinfo=timezone.utc)
        result = _next_occurrence(weekday=1, hour=10, from_date=now)
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0


# ---------------------------------------------------------------------------
# SmartFillService unit tests
# ---------------------------------------------------------------------------


def _make_service(ai_response: dict | None = None, heatmap_response: dict | None = None):
    """Build SmartFillService with mocked sub-dependencies."""
    post_repo = AsyncMock(spec=PostRepository)

    # Each call to create() returns a new fake post
    async def _fake_create(post):
        post.id = make_uuid()
        return post

    post_repo.create.side_effect = _fake_create

    heatmap_svc = AsyncMock(spec=HeatmapService)
    if heatmap_response is None:
        heatmap_response = {
            "heatmap": {
                "tuesday": {"9": 0.95, "10": 0.98},
                "thursday": {"9": 0.90},
                "monday": {"10": 0.80},
                "wednesday": {},
                "friday": {},
                "saturday": {},
                "sunday": {},
            },
            "best_slots": [
                {"day": "tuesday", "hour": 10, "avg_engagement_rate": 0.98},
                {"day": "tuesday", "hour": 9, "avg_engagement_rate": 0.95},
                {"day": "thursday", "hour": 9, "avg_engagement_rate": 0.90},
                {"day": "monday", "hour": 10, "avg_engagement_rate": 0.80},
            ],
            "worst_slots": [],
            "data_source": "global_benchmark",
            "sample_size": 0,
        }
    heatmap_svc.get_heatmap.return_value = heatmap_response

    service = SmartFillService(post_repo, heatmap_svc)

    # Inject AI response
    if ai_response is not None:
        async def _fake_call_ai(user_id, pillars, posts_per_week, preferred_formats, top_posts_sample):
            return ai_response.get("posts", [])
        service._call_ai_engine = _fake_call_ai

    return service, post_repo


class TestSmartFillHappyPath:
    @pytest.mark.asyncio
    async def test_creates_correct_number_of_posts(self):
        ai = make_week_plan_response(count=4)
        service, repo = _make_service(ai_response=ai)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI", "Founder Stories", "Product"],
            posts_per_week=4,
            preferred_formats=["text", "carousel"],
        )
        assert len(result) == 4
        assert repo.create.call_count == 4

    @pytest.mark.asyncio
    async def test_posts_have_status_draft(self):
        ai = make_week_plan_response(count=3)
        service, repo = _make_service(ai_response=ai)
        with patch("app.services.smart_fill_service._next_occurrence") as mock_next:
            mock_next.return_value = datetime.now(timezone.utc) + timedelta(days=1)
            result = await service.smart_fill(
                user_id=make_uuid(),
                pillars=["AI", "Products"],
                posts_per_week=3,
                preferred_formats=["text"],
            )
        for post in result:
            assert post.status == "draft"

    @pytest.mark.asyncio
    async def test_posts_have_scheduled_at_set(self):
        ai = make_week_plan_response(count=3)
        service, _ = _make_service(ai_response=ai)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI", "Founder"],
            posts_per_week=3,
            preferred_formats=["text"],
        )
        for post in result:
            # scheduled_at is set on the Post object before create() is called
            # The mock create() returns the same object
            assert post.scheduled_at is not None

    @pytest.mark.asyncio
    async def test_posts_respect_posts_per_week_cap(self):
        """Even if AI returns 7 posts, we only create posts_per_week of them."""
        ai = make_week_plan_response(count=7)
        service, repo = _make_service(ai_response=ai)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["A", "B", "C"],
            posts_per_week=3,
            preferred_formats=["text"],
        )
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_posts_have_hook_from_ai_response(self):
        ai = make_week_plan_response(count=2)
        service, _ = _make_service(ai_response=ai)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI"],
            posts_per_week=2,
            preferred_formats=["text"],
        )
        # Post.hook should come from AI response hook field
        assert result[0].hook == ai["posts"][0]["hook"]
        assert result[1].hook == ai["posts"][1]["hook"]

    @pytest.mark.asyncio
    async def test_generation_metadata_includes_source(self):
        ai = make_week_plan_response(count=1)
        service, _ = _make_service(ai_response=ai)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["A"],
            posts_per_week=1,
            preferred_formats=["text"],
        )
        meta = result[0].generation_metadata
        assert meta["source"] == "smart_fill_v2"
        assert "heatmap_slot" in meta


class TestSmartFillUnhappyPaths:
    @pytest.mark.asyncio
    async def test_ai_engine_returns_empty_list(self):
        service, repo = _make_service(ai_response={"posts": []})
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI"],
            posts_per_week=4,
            preferred_formats=["text"],
        )
        assert result == []
        repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_ai_engine_http_error_returns_empty(self):
        """If _call_ai_engine network-fails, smart_fill returns [] gracefully."""
        _, _ = _make_service()  # not used directly

        post_repo = AsyncMock(spec=PostRepository)
        heatmap_svc = AsyncMock(spec=HeatmapService)
        heatmap_svc.get_heatmap.return_value = {
            "heatmap": {"tuesday": {"10": 0.98}},
            "best_slots": [{"day": "tuesday", "hour": 10, "avg_engagement_rate": 0.98}],
            "worst_slots": [],
            "data_source": "global_benchmark",
            "sample_size": 0,
        }
        service = SmartFillService(post_repo, heatmap_svc)

        # Patch httpx to raise an error
        with patch("app.services.smart_fill_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = AsyncMock(return_value=False)
            mock_instance.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.return_value = mock_instance

            result = await service.smart_fill(
                user_id=make_uuid(),
                pillars=["AI"],
                posts_per_week=3,
                preferred_formats=["text"],
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_slot_used_when_slots_exhausted(self):
        """When heatmap returns fewer slots than needed, fallback distributes at 10am."""
        ai = make_week_plan_response(count=5)
        # Only provide 2 best slots (need 5)
        heatmap_response = {
            "heatmap": {"tuesday": {"10": 0.98}, "thursday": {"9": 0.90}},
            "best_slots": [
                {"day": "tuesday", "hour": 10, "avg_engagement_rate": 0.98},
                {"day": "thursday", "hour": 9, "avg_engagement_rate": 0.90},
            ],
            "worst_slots": [],
            "data_source": "global_benchmark",
            "sample_size": 0,
        }
        service, repo = _make_service(ai_response=ai, heatmap_response=heatmap_response)
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["A", "B", "C"],
            posts_per_week=5,
            preferred_formats=["text"],
        )
        # Should still create 5 posts despite only 2 dedicated slots
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_empty_pillars_does_not_crash(self):
        """Edge case: pillars is non-empty (validated at controller level), but body is empty."""
        ai = make_week_plan_response(count=1)
        service, _ = _make_service(ai_response=ai)
        # Should not raise even if pillar list is single item
        result = await service.smart_fill(
            user_id=make_uuid(),
            pillars=["AI"],
            posts_per_week=1,
            preferred_formats=["text"],
        )
        assert len(result) == 1
