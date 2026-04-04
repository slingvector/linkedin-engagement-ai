"""AI Engine V2 — shared fixtures and factories for AI Engine test suite."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def make_llm_service_mock(return_value: dict | None = None) -> MagicMock:
    """Create a mock LLMService that returns a fixed JSON dict."""
    llm = AsyncMock()
    llm.generate_structured_json.return_value = return_value or {}
    return llm


def make_carousel_outline_payload() -> dict:
    return {
        "cover_hook": "The 7-step framework that made my startup $1M ARR",
        "cta_slide_text": "Follow me for more growth frameworks →",
        "slides": [
            {
                "slide_number": i,
                "headline": f"Step {i}: Action headline",
                "body": f"Short body text for slide {i}.",
                "visual_suggestion": "Abstract illustration.",
            }
            for i in range(1, 8)
        ],
    }


def make_virality_score_payload(total_score: int = 74) -> dict:
    return {
        "total_score": total_score,
        "breakdown": {
            "hook_strength": 22,
            "readability": 18,
            "value_density": 24,
            "cta_quality": 10,
        },
        "hook_alternatives": [
            {"hook": "The AI framework nobody teaches", "predicted_score": 87},
            {"hook": "I built a $1M product using this rule", "predicted_score": 82},
            {"hook": "Stop doing X. Start doing Y instead", "predicted_score": 79},
        ],
        "reasoning": "Hook lacks curiosity gap. Readability strong.",
    }


def make_week_plan_payload(count: int = 4) -> dict:
    return {
        "posts": [
            {
                "pillar": "AI Automation",
                "format": "text" if i % 2 == 0 else "carousel",
                "topic": f"Topic {i + 1}",
                "hook": f"Hook for post {i + 1} with strong curiosity",
                "body": "• Point one\n• Point two\n• Point three",
                "cta": "What's your experience?",
            }
            for i in range(count)
        ]
    }


# ---------------------------------------------------------------------------
# App client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


AI_API_KEY_HEADER = {"X-AI-API-Key": "test-key"}
