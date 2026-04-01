"""
SmartFill Service — Core API V2
Orchestrates: heatmap slot selection → AI Engine week plan → bulk post draft creation.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from uuid import UUID

import httpx
import structlog

from app.config import get_settings
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.services.heatmap_service import HeatmapService, _best_slots

logger = structlog.get_logger()

_DAY_TO_WEEKDAY = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


def _next_occurrence(weekday: int, hour: int, from_date: datetime) -> datetime:
    """Return the next datetime for a given weekday+hour at or after from_date."""
    days_ahead = (weekday - from_date.weekday()) % 7
    target = from_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    target += timedelta(days=days_ahead)
    if target < from_date:
        target += timedelta(weeks=1)
    return target


class SmartFillService:
    """
    Main orchestrator for the Smart Fill Calendar feature.

    Flow:
    1. Call AI Engine → get N posts with pillar/format/hook/body/cta
    2. Call HeatmapService → get top N available slots for the coming week
    3. Pair each AI post with a heatmap slot
    4. Bulk-create Post records with status="draft" and scheduled_at set
    5. Return all created Post records
    """

    def __init__(self, post_repo: PostRepository, heatmap_service: HeatmapService):
        self._repo = post_repo
        self._heatmap = heatmap_service
        self._settings = get_settings()

    async def smart_fill(
        self,
        user_id: UUID,
        pillars: list[str],
        posts_per_week: int,
        preferred_formats: list[str],
        top_posts_sample: list[str] | None = None,
    ) -> list[Post]:
        """Run the complete Smart Fill pipeline. Returns created draft Post records."""

        # ── 1. Get heatmap best slots ─────────────────────────────────────
        heatmap_data = await self._heatmap.get_heatmap(user_id, weeks=8)
        best = _best_slots(heatmap_data["heatmap"], n=posts_per_week + 3)  # extra buffer

        # ── 2. Call AI Engine for week plan ───────────────────────────────
        ai_posts = await self._call_ai_engine(
            user_id=user_id,
            pillars=pillars,
            posts_per_week=posts_per_week,
            preferred_formats=preferred_formats,
            top_posts_sample=top_posts_sample or [],
        )

        if not ai_posts:
            logger.warning("smart_fill_no_ai_posts", user_id=str(user_id))
            return []

        # ── 3. Match each AI post to the next available heatmap slot ──────
        now = datetime.now(timezone.utc)
        used_slots: set[str] = set()
        slot_queue = list(best)

        created: list[Post] = []
        for i, ai_post in enumerate(ai_posts[:posts_per_week]):
            # Find next unused slot
            slot = None
            for candidate in slot_queue:
                key = f"{candidate['day']}-{candidate['hour']}"
                if key not in used_slots:
                    slot = candidate
                    used_slots.add(key)
                    break

            if not slot:
                # Fallback: distribute evenly across next N days at 10am
                slot = {"day": list(_DAY_TO_WEEKDAY.keys())[i % 5], "hour": 10}

            weekday = _DAY_TO_WEEKDAY.get(slot["day"], 1)
            scheduled_at = _next_occurrence(weekday, slot["hour"], now).replace(tzinfo=None)

            post = Post(
                user_id=user_id,
                hook=ai_post.get("hook", ""),
                body_content=ai_post.get("body", ""),
                call_to_action=ai_post.get("cta", ""),
                topic=ai_post.get("topic", pillars[i % len(pillars)]),
                audience="LinkedIn professionals",
                framework="smart_fill",
                tone="professional_but_conversational",
                status="draft",
                scheduled_at=scheduled_at,
                generation_metadata={
                    "pillar": ai_post.get("pillar"),
                    "format": ai_post.get("format", "text"),
                    "source": "smart_fill_v2",
                    "heatmap_slot": slot,
                },
            )

            created_post = await self._repo.create(post)
            created.append(created_post)
            logger.info(
                "smart_fill_post_created",
                post_id=str(created_post.id),
                topic=post.topic,
                scheduled_at=scheduled_at.isoformat(),
            )

        return created

    async def _call_ai_engine(
        self,
        user_id: UUID,
        pillars: list[str],
        posts_per_week: int,
        preferred_formats: list[str],
        top_posts_sample: list[str],
    ) -> list[dict]:
        """Call AI Engine week-plan webhook and return raw post dicts."""
        url = f"{self._settings.ai_engine_url}/webhooks/v2/generate/week-plan"
        headers = {"X-AI-API-Key": self._settings.ai_engine_api_key}
        payload = {
            "user_id": str(user_id),
            "pillars": pillars,
            "posts_per_week": posts_per_week,
            "preferred_formats": preferred_formats,
            "top_posts_sample": top_posts_sample,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("posts", [])
        except Exception as e:
            logger.error("smart_fill_ai_engine_call_failed", error=str(e))
            return []
