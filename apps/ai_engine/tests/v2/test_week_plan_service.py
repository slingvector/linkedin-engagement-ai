"""AI Engine — WeekPlanService unit tests.

Coverage:
  - generate_week_plan() happy path: returns N posts matching request.posts_per_week
  - generate_week_plan() top_posts_sample injected into user_prompt
  - generate_week_plan() empty top_posts_sample → no tone section
  - generate_week_plan() LLM returns fewer posts than requested → returns what it got
  - generate_week_plan() pillar defaults to first pillar when missing from LLM
  - generate_week_plan() format defaults to 'text' when missing
  - generate_week_plan() LLM RuntimeError propagated
  - WeekPlanPost schema validation (pillar, format, hook, body, cta, topic)
  - generate_week_plan() temperature is high (0.7+) for creative variety
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.services.week_plan_service import (
    WeekPlanService,
    WeekPlanRequest,
    WeekPlanResponse,
    WeekPlanPost,
)

from tests.v2.conftest import make_llm_service_mock, make_week_plan_payload


def _make_request(
    pillars: list[str] | None = None,
    posts_per_week: int = 4,
    preferred_formats: list[str] | None = None,
    top_posts_sample: list[str] | None = None,
) -> WeekPlanRequest:
    return WeekPlanRequest(
        user_id="user-abc",
        pillars=pillars or ["AI Automation", "Founder Stories", "Product Tips"],
        posts_per_week=posts_per_week,
        preferred_formats=preferred_formats or ["text", "carousel"],
        top_posts_sample=top_posts_sample or [],
    )


class TestWeekPlanServiceHappyPath:
    @pytest.mark.asyncio
    async def test_returns_week_plan_response(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=4))
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request())
        assert isinstance(result, WeekPlanResponse)

    @pytest.mark.asyncio
    async def test_correct_number_of_posts(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=4))
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request(posts_per_week=4))
        assert len(result.posts) == 4

    @pytest.mark.asyncio
    async def test_each_post_has_required_fields(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=3))
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request(posts_per_week=3))
        for post in result.posts:
            assert isinstance(post, WeekPlanPost)
            assert post.pillar != ""
            assert post.format in ("text", "carousel", "video")
            assert post.hook != ""
            assert post.body != ""
            assert post.cta != ""
            assert post.topic != ""

    @pytest.mark.asyncio
    async def test_top_posts_sample_in_user_prompt(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=2))
        service = WeekPlanService(llm)
        await service.generate_week_plan(
            _make_request(top_posts_sample=["Best hook I ever wrote", "Second best"])
        )
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "Best hook I ever wrote" in user_prompt

    @pytest.mark.asyncio
    async def test_empty_top_posts_sample_no_tone_section(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=3))
        service = WeekPlanService(llm)
        await service.generate_week_plan(_make_request(top_posts_sample=[]))
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "Top performing posts" not in user_prompt

    @pytest.mark.asyncio
    async def test_high_temperature_for_creativity(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=4))
        service = WeekPlanService(llm)
        await service.generate_week_plan(_make_request())
        temp = llm.generate_structured_json.call_args.kwargs.get("temperature", 0)
        assert temp >= 0.7, f"Expected high temperature >= 0.7, got {temp}"

    @pytest.mark.asyncio
    async def test_pillars_in_system_prompt(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=2))
        service = WeekPlanService(llm)
        await service.generate_week_plan(
            _make_request(pillars=["AI Automation", "Founder Stories"])
        )
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "AI Automation" in user_prompt
        assert "Founder Stories" in user_prompt

    @pytest.mark.asyncio
    async def test_preferred_formats_in_prompt(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=2))
        service = WeekPlanService(llm)
        await service.generate_week_plan(
            _make_request(preferred_formats=["carousel", "video"])
        )
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "carousel" in user_prompt
        assert "video" in user_prompt


class TestWeekPlanServiceEdgeCases:
    @pytest.mark.asyncio
    async def test_llm_returns_fewer_posts_than_requested(self):
        """LLM returns 2 posts but 5 requested — service returns what it got."""
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=2))
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request(posts_per_week=5))
        assert len(result.posts) == 2

    @pytest.mark.asyncio
    async def test_missing_pillar_defaults_to_first_pillar(self):
        payload = {
            "posts": [
                {
                    "format": "text",
                    "topic": "Topic",
                    "hook": "Some hook",
                    "body": "body",
                    "cta": "cta",
                    # "pillar" missing
                }
            ]
        }
        llm = make_llm_service_mock(return_value=payload)
        service = WeekPlanService(llm)
        req = _make_request(pillars=["AI Automation", "Founder"], posts_per_week=1)
        result = await service.generate_week_plan(req)
        assert result.posts[0].pillar == "AI Automation"

    @pytest.mark.asyncio
    async def test_missing_format_defaults_to_text(self):
        payload = {
            "posts": [
                {
                    "pillar": "AI",
                    "topic": "Topic",
                    "hook": "hook",
                    "body": "body",
                    "cta": "cta",
                    # "format" missing
                }
            ]
        }
        llm = make_llm_service_mock(return_value=payload)
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request(posts_per_week=1))
        assert result.posts[0].format == "text"

    @pytest.mark.asyncio
    async def test_missing_topic_defaults_to_linkedin_post(self):
        payload = {
            "posts": [
                {
                    "pillar": "AI",
                    "format": "text",
                    "hook": "hook",
                    "body": "body",
                    "cta": "cta",
                    # "topic" missing
                }
            ]
        }
        llm = make_llm_service_mock(return_value=payload)
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request(posts_per_week=1))
        assert result.posts[0].topic == "LinkedIn Post"

    @pytest.mark.asyncio
    async def test_llm_returns_empty_posts(self):
        llm = make_llm_service_mock(return_value={"posts": []})
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(_make_request())
        assert result.posts == []

    @pytest.mark.asyncio
    async def test_llm_runtime_error_propagated(self):
        llm = AsyncMock()
        llm.generate_structured_json.side_effect = RuntimeError("LLM unavailable")
        service = WeekPlanService(llm)
        with pytest.raises(RuntimeError):
            await service.generate_week_plan(_make_request())

    @pytest.mark.asyncio
    async def test_single_pillar_works(self):
        llm = make_llm_service_mock(return_value=make_week_plan_payload(count=3))
        service = WeekPlanService(llm)
        result = await service.generate_week_plan(
            _make_request(pillars=["AI Automation"], posts_per_week=3)
        )
        assert len(result.posts) == 3
