"""AI Engine — ViralityScoreService unit tests.

Coverage:
  - score_post() happy path: correct total_score, breakdown, hook_alternatives
  - score_post() top_posts_sample injected into user_prompt
  - score_post() LLM runtime error propagated
  - breakdown fields: hook_strength(0-30), readability(0-20), value_density(0-30), cta_quality(0-20)
  - total_score fallback computation (sum of breakdown when total_score key missing)
  - hook_alternatives capped at 3
  - invalid int values in breakdown → int() coercion
  - empty top_posts_sample → no tone section in prompt
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.virality_score_service import (
    ViralityScoreService,
    ScoreRequest,
    ScoreResponse,
    ScoreBreakdown,
    HookAlternative,
)

from tests.v2.conftest import make_llm_service_mock, make_virality_score_payload


def _make_request(
    draft_text: str = "Test hook\n\nTest body\n\nTest CTA",
    top_posts_sample: list[str] | None = None,
) -> ScoreRequest:
    return ScoreRequest(
        user_id="user-123",
        post_id="post-456",
        draft_text=draft_text,
        top_posts_sample=top_posts_sample or [],
    )


class TestViralityScoreServiceHappyPath:
    @pytest.mark.asyncio
    async def test_returns_score_response(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert isinstance(result, ScoreResponse)

    @pytest.mark.asyncio
    async def test_total_score_matches_payload(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload(total_score=74))
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.total_score == 74

    @pytest.mark.asyncio
    async def test_breakdown_fields_correct(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.breakdown.hook_strength == 22
        assert result.breakdown.readability == 18
        assert result.breakdown.value_density == 24
        assert result.breakdown.cta_quality == 10

    @pytest.mark.asyncio
    async def test_hook_alternatives_count_is_three(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert len(result.hook_alternatives) == 3

    @pytest.mark.asyncio
    async def test_hook_alternatives_have_predicted_score(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        for alt in result.hook_alternatives:
            assert isinstance(alt, HookAlternative)
            assert isinstance(alt.predicted_score, int)
            assert 0 <= alt.predicted_score <= 100

    @pytest.mark.asyncio
    async def test_reasoning_is_non_empty(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.reasoning != ""

    @pytest.mark.asyncio
    async def test_temperature_low_for_consistency(self):
        """Score endpoint should use low temp for repeatable scoring."""
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        await service.score_post(_make_request())
        call_kwargs = llm.generate_structured_json.call_args.kwargs
        assert call_kwargs.get("temperature") <= 0.5

    @pytest.mark.asyncio
    async def test_top_posts_sample_included_in_prompt(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        top_posts = ["Top hook 1", "Top hook 2"]
        await service.score_post(_make_request(top_posts_sample=top_posts))
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "Top hook 1" in user_prompt
        assert "Top hook 2" in user_prompt

    @pytest.mark.asyncio
    async def test_empty_top_posts_sample_no_tone_section(self):
        llm = make_llm_service_mock(return_value=make_virality_score_payload())
        service = ViralityScoreService(llm)
        await service.score_post(_make_request(top_posts_sample=[]))
        user_prompt = llm.generate_structured_json.call_args.kwargs["user_prompt"]
        assert "Top performing posts" not in user_prompt


class TestViralityScoreServiceEdgeCases:
    @pytest.mark.asyncio
    async def test_total_score_fallback_from_breakdown_sum(self):
        """If LLM omits total_score, we compute it from breakdown sum."""
        payload = {
            "breakdown": {
                "hook_strength": 20,
                "readability": 15,
                "value_density": 25,
                "cta_quality": 15,
            },
            "hook_alternatives": [
                {"hook": "h1", "predicted_score": 80},
                {"hook": "h2", "predicted_score": 75},
                {"hook": "h3", "predicted_score": 70},
            ],
            "reasoning": "Some reasoning",
        }
        llm = make_llm_service_mock(return_value=payload)
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.total_score == 75  # 20+15+25+15

    @pytest.mark.asyncio
    async def test_hook_alternatives_capped_at_three(self):
        """Even if LLM returns 5 alternatives, we only take first 3."""
        payload = make_virality_score_payload()
        payload["hook_alternatives"] = [
            {"hook": f"Hook {i}", "predicted_score": 80 - i}
            for i in range(5)
        ]
        llm = make_llm_service_mock(return_value=payload)
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert len(result.hook_alternatives) == 3

    @pytest.mark.asyncio
    async def test_llm_runtime_error_propagated(self):
        llm = AsyncMock()
        llm.generate_structured_json.side_effect = RuntimeError("LLM error")
        service = ViralityScoreService(llm)
        with pytest.raises(RuntimeError):
            await service.score_post(_make_request())

    @pytest.mark.asyncio
    async def test_breakdown_int_coercion_from_float(self):
        """LLM might return floats; int() coercion should not crash."""
        payload = {
            "total_score": 74,
            "breakdown": {
                "hook_strength": 22.5,  # float returned by LLM
                "readability": 18.0,
                "value_density": 24.7,
                "cta_quality": 10.1,
            },
            "hook_alternatives": [{"hook": "h", "predicted_score": 80}],
            "reasoning": "r",
        }
        llm = make_llm_service_mock(return_value=payload)
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert isinstance(result.breakdown.hook_strength, int)
        assert result.breakdown.hook_strength == 22

    @pytest.mark.asyncio
    async def test_missing_breakdown_key_defaults_to_zero(self):
        """If 'hook_strength' is missing from breakdown, should default to 0."""
        payload = {
            "total_score": 50,
            "breakdown": {
                # missing hook_strength
                "readability": 18,
                "value_density": 24,
                "cta_quality": 10,
            },
            "hook_alternatives": [],
            "reasoning": "incomplete",
        }
        llm = make_llm_service_mock(return_value=payload)
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.breakdown.hook_strength == 0

    @pytest.mark.asyncio
    async def test_empty_hook_alternatives_returns_empty_list(self):
        payload = make_virality_score_payload()
        payload["hook_alternatives"] = []
        llm = make_llm_service_mock(return_value=payload)
        service = ViralityScoreService(llm)
        result = await service.score_post(_make_request())
        assert result.hook_alternatives == []
