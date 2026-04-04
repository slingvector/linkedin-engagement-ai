"""
Shared fixtures and factory helpers for the V2 test suite.

All tests in this directory mock:
  - DB session (AsyncSession) — via AsyncMock
  - PostRepository — via MagicMock / AsyncMock
  - httpx.AsyncClient — via AsyncMock (to freeze AI Engine + LinkedIn API calls)
  - get_current_user dependency — returns a fake User
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Factory helpers — build minimal model instances without hitting a real DB
# ---------------------------------------------------------------------------


def make_uuid() -> uuid.UUID:
    return uuid.uuid4()


def make_user(
    user_id: uuid.UUID | None = None,
    access_token_encrypted: str | bytes | None = b"encrypted_token",
) -> MagicMock:
    """Return a mock User ORM instance."""
    user = MagicMock()
    user.id = user_id or make_uuid()
    user.email = "test@example.com"
    user.access_token_encrypted = access_token_encrypted
    return user


def make_post(
    post_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str = "draft",
    hook: str = "Test hook",
    body_content: str = "Test body",
    call_to_action: str = "What do you think?",
    topic: str = "AI Automation",
    audience: str = "LinkedIn professionals",
    tone: str = "professional_but_conversational",
    framework: str = "smart_fill",
    impressions: int = 100,
    virality_score: int | None = None,
    score_breakdown: dict | None = None,
    hook_alternatives: list | None = None,
) -> MagicMock:
    """Return a mock Post ORM instance."""
    post = MagicMock()
    post.id = post_id or make_uuid()
    post.user_id = user_id or make_uuid()
    post.status = status
    post.hook = hook
    post.body_content = body_content
    post.call_to_action = call_to_action
    post.topic = topic
    post.audience = audience
    post.tone = tone
    post.framework = framework
    post.impressions = impressions
    post.virality_score = virality_score
    post.score_breakdown = score_breakdown
    post.hook_alternatives = hook_alternatives or []
    post.score_updated_at = None
    post.scheduled_at = None
    post.published_at = None
    post.created_at = datetime.now(timezone.utc)
    post.deleted_at = None
    return post


def make_carousel_asset(
    asset_id: uuid.UUID | None = None,
    post_id: uuid.UUID | None = None,
    status: str = "rendered",
    slides_json: list | None = None,
    pdf_url: str | None = "file:///tmp/carousel_pdfs/test.pdf",
    linkedin_asset_urn: str | None = None,
    brand_kit_snapshot: dict | None = None,
    slide_count: int = 7,
) -> MagicMock:
    """Return a mock CarouselAsset ORM instance."""
    asset = MagicMock()
    asset.id = asset_id or make_uuid()
    asset.post_id = post_id or make_uuid()
    asset.status = status
    asset.slides_json = slides_json or _default_slides()
    asset.pdf_url = pdf_url
    asset.linkedin_asset_urn = linkedin_asset_urn
    asset.brand_kit_snapshot = brand_kit_snapshot or {"primary_color": "#0A66C2", "font_family": "Inter"}
    asset.slide_count = slide_count
    asset.created_at = datetime.now(timezone.utc)
    asset.deleted_at = None
    return asset


def make_user_settings(
    user_id: uuid.UUID | None = None,
    primary_color: str = "#FF5733",
    logo_url: str | None = None,
    font_family: str = "Roboto",
    author_name: str = "Test Author",
    author_tagline: str = "AI Enthusiast",
) -> MagicMock:
    """Return a mock UserSettings ORM instance."""
    settings = MagicMock()
    settings.user_id = user_id or make_uuid()
    settings.primary_color = primary_color
    settings.logo_url = logo_url
    settings.font_family = font_family
    settings.author_name = author_name
    settings.author_tagline = author_tagline
    return settings


def _default_slides(count: int = 7) -> list[dict]:
    slides = []
    for i in range(1, count + 1):
        slides.append({
            "slide_number": i,
            "headline": f"Slide {i} Headline",
            "body": f"Body text for slide {i}.",
            "visual_suggestion": "A clean infographic.",
        })
    return slides


def make_ai_outline_response(slide_count: int = 7) -> dict:
    """Simulate the JSON payload returned by AI Engine /carousel-outline."""
    return {
        "slides": _default_slides(slide_count),
        "cover_hook": "Hook that stops the scroll",
        "cta_slide_text": "Follow for more insights →",
    }


def make_virality_score_response(total_score: int = 74) -> dict:
    """Simulate the JSON payload returned by AI Engine /score/post."""
    return {
        "total_score": total_score,
        "breakdown": {
            "hook_strength": 22,
            "readability": 18,
            "value_density": 24,
            "cta_quality": 10,
        },
        "hook_alternatives": [
            {"hook": "AI Automation: The Great Equalizer?", "predicted_score": 87},
            {"hook": "I Almost Lost My Startup to AI", "predicted_score": 79},
            {"hook": "The Dirty Secret of AI Nobody Talks About", "predicted_score": 82},
        ],
        "reasoning": "The hook lacks curiosity gap. Readability is good.",
    }


def make_week_plan_response(count: int = 4) -> dict:
    """Simulate the JSON payload returned by AI Engine /generate/week-plan."""
    pillars = ["AI Automation", "Founder Stories", "Product Tips", "Leadership"]
    formats = ["text", "carousel", "text", "carousel"]
    posts = [
        {
            "pillar": pillars[i % len(pillars)],
            "format": formats[i % len(formats)],
            "topic": f"Topic {i + 1}",
            "hook": f"Compelling hook number {i + 1} — read this",
            "body": "• Point 1\n• Point 2\n• Point 3",
            "cta": "What's your take?",
        }
        for i in range(count)
    ]
    return {"posts": posts}


# ---------------------------------------------------------------------------
# Async DB session mock helpers
# ---------------------------------------------------------------------------


def make_db_session() -> AsyncMock:
    """Create a fully mocked AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def db_scalar_result(value: Any) -> MagicMock:
    """Wrap value in a mock that looks like an SQLAlchemy scalar result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# Common pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user():
    return make_user()


@pytest.fixture
def sample_post(user):
    return make_post(user_id=user.id)


@pytest.fixture
def sample_carousel_asset(sample_post):
    return make_carousel_asset(post_id=sample_post.id)


@pytest.fixture
def db():
    return make_db_session()
