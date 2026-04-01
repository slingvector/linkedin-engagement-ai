"""AI Engine — CarouselOutlineService unit tests.

Coverage:
  - generate_outline() happy path: returns 7 slides with correct shape
  - generate_outline() slide count respects request.slide_count
  - generate_outline() missing slides in LLM response → empty slides list
  - generate_outline() cover_hook falls back to first slide headline
  - generate_outline() cta_slide_text defaults to 'Follow for more →'
  - generate_outline() LLM raises RuntimeError → propagated
  - Slide schema validation: slide_number, headline, body, visual_suggestion
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.carousel_outline_service import (
    CarouselOutlineService,
    CarouselOutlineRequest,
    CarouselOutlineResponse,
    Slide,
)

from tests.v2.conftest import make_llm_service_mock, make_carousel_outline_payload


def _make_request(slide_count: int = 7) -> CarouselOutlineRequest:
    return CarouselOutlineRequest(
        user_id="user-123",
        topic="AI Automation for Founders",
        audience="Startup founders and senior operators",
        tone="professional_but_conversational",
        slide_count=slide_count,
    )


class TestCarouselOutlineServiceHappyPath:
    @pytest.mark.asyncio
    async def test_returns_carousel_outline_response(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert isinstance(result, CarouselOutlineResponse)

    @pytest.mark.asyncio
    async def test_returns_seven_slides(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request(slide_count=7))
        assert len(result.slides) == 7

    @pytest.mark.asyncio
    async def test_slide_numbers_are_sequential(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        for i, slide in enumerate(result.slides, start=1):
            assert slide.slide_number == i

    @pytest.mark.asyncio
    async def test_each_slide_has_required_fields(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        for slide in result.slides:
            assert isinstance(slide, Slide)
            assert slide.headline != ""
            assert slide.body != ""
            assert slide.visual_suggestion != ""

    @pytest.mark.asyncio
    async def test_cover_hook_is_set(self):
        payload = make_carousel_outline_payload()
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.cover_hook == payload["cover_hook"]

    @pytest.mark.asyncio
    async def test_cta_slide_text_is_set(self):
        payload = make_carousel_outline_payload()
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.cta_slide_text == payload["cta_slide_text"]

    @pytest.mark.asyncio
    async def test_llm_called_with_correct_temperature(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        await service.generate_outline(_make_request())
        call_kwargs = llm.generate_structured_json.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.7

    @pytest.mark.asyncio
    async def test_llm_called_with_system_prompt(self):
        llm = make_llm_service_mock(return_value=make_carousel_outline_payload())
        service = CarouselOutlineService(llm)
        await service.generate_outline(_make_request())
        call_kwargs = llm.generate_structured_json.call_args.kwargs
        assert "carousel" in call_kwargs.get("system_prompt", "").lower()


class TestCarouselOutlineServiceEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_slides_from_llm(self):
        llm = make_llm_service_mock(return_value={"slides": [], "cover_hook": "", "cta_slide_text": ""})
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.slides == []

    @pytest.mark.asyncio
    async def test_cover_hook_falls_back_to_first_slide_headline_when_key_missing(self):
        """When 'cover_hook' key is entirely absent from LLM response, fallback to slide[0].headline."""
        payload = make_carousel_outline_payload()
        del payload["cover_hook"]  # completely absent → dict.get() uses default
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        # .get("cover_hook", slides[0].headline) → slides[0].headline is used
        assert result.cover_hook == payload["slides"][0]["headline"]

    @pytest.mark.asyncio
    async def test_cover_hook_empty_string_preserved(self):
        """When LLM returns cover_hook='' (key present), service preserves empty string."""
        payload = make_carousel_outline_payload()
        payload["cover_hook"] = ""  # key present but empty → dict.get returns ""
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.cover_hook == ""

    @pytest.mark.asyncio
    async def test_cta_defaults_to_follow_for_more(self):
        payload = make_carousel_outline_payload()
        del payload["cta_slide_text"]
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert "follow" in result.cta_slide_text.lower()

    @pytest.mark.asyncio
    async def test_llm_runtime_error_propagated(self):
        llm = AsyncMock()
        llm.generate_structured_json.side_effect = RuntimeError("LLM call failed after 3 retries")
        service = CarouselOutlineService(llm)
        with pytest.raises(RuntimeError):
            await service.generate_outline(_make_request())

    @pytest.mark.asyncio
    async def test_partial_slide_missing_headline_filled_with_empty_string(self):
        """LLM returns a slide without 'headline' key — should default to empty string."""
        payload = {
            "slides": [{"slide_number": 1, "body": "some body", "visual_suggestion": "image"}],
            "cover_hook": "hook",
            "cta_slide_text": "follow",
        }
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.slides[0].headline == ""

    @pytest.mark.asyncio
    async def test_slide_number_auto_assigned_when_missing(self):
        """Slides without slide_number should get auto-incremented numbers."""
        payload = {
            "slides": [
                {"headline": "H1", "body": "B1", "visual_suggestion": "V1"},
                {"headline": "H2", "body": "B2", "visual_suggestion": "V2"},
            ],
            "cover_hook": "H1",
            "cta_slide_text": "follow",
        }
        llm = make_llm_service_mock(return_value=payload)
        service = CarouselOutlineService(llm)
        result = await service.generate_outline(_make_request())
        assert result.slides[0].slide_number == 1
        assert result.slides[1].slide_number == 2
