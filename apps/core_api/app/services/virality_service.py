"""
ViralityService — Core API V2
Orchestrates: build draft text → call AI Engine scorer → persist score to post → return.
"""

from datetime import datetime, timezone
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.post import Post
from app.repositories.post_repository import PostRepository

logger = structlog.get_logger()


def _assemble_draft_text(post: Post) -> str:
    """Assemble full post text for scoring."""
    parts = [post.hook, post.body_content]
    if post.call_to_action:
        parts.append(post.call_to_action)
    return "\n\n".join(parts)


class ViralityService:
    """
    Scores a draft post against the AI Engine's virality model.

    Flow:
    1. Load the post from DB (validates user ownership)
    2. Fetch user's top 3 published posts by impressions (for tone calibration)
    3. Call AI Engine /webhooks/v2/score/post
    4. Persist score + breakdown + alternatives to post record
    5. Return updated post
    """

    def __init__(self, post_repo: PostRepository, db: AsyncSession):
        self._repo = post_repo
        self._db = db
        self._settings = get_settings()

    async def score_post(self, post_id: UUID, user_id: UUID) -> Post:
        """Score a post and persist the result. Returns the updated Post."""

        # ── 1. Load post ──────────────────────────────────────────────────────
        post = await self._repo.get_by_id(post_id, user_id)
        if not post:
            raise ValueError(f"Post {post_id} not found for user {user_id}")

        # ── 2. Get top performers for tone calibration ────────────────────────
        top_hooks = await self._get_top_hooks(user_id)

        # ── 3. Call AI Engine ─────────────────────────────────────────────────
        draft_text = _assemble_draft_text(post)
        score_data = await self._call_ai_engine(
            user_id=user_id,
            post_id=post_id,
            draft_text=draft_text,
            top_posts_sample=top_hooks,
        )

        if not score_data:
            logger.warning("virality_score_failed", post_id=str(post_id))
            return post

        # ── 4. Persist score ──────────────────────────────────────────────────
        post.virality_score = score_data.get("total_score")
        post.score_breakdown = score_data.get("breakdown")
        post.hook_alternatives = score_data.get("hook_alternatives", [])
        post.score_updated_at = datetime.now(timezone.utc)

        updated = await self._repo.update(post)

        logger.info(
            "virality_score_persisted",
            post_id=str(post_id),
            score=post.virality_score,
        )

        return updated

    async def _get_top_hooks(self, user_id: UUID, limit: int = 3) -> list[str]:
        """Fetch the hooks of top-performing published posts for tone calibration."""
        try:
            result = await self._db.execute(
                select(Post.hook)
                .where(
                    Post.user_id == user_id,
                    Post.status == "published",
                    Post.impressions > 0,
                    Post.deleted_at.is_(None),
                )
                .order_by(desc(Post.impressions))
                .limit(limit)
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning("top_hooks_fetch_failed", error=str(e))
            return []

    async def _call_ai_engine(
        self,
        user_id: UUID,
        post_id: UUID,
        draft_text: str,
        top_posts_sample: list[str],
    ) -> dict | None:
        """Call AI Engine score endpoint and return raw JSON dict."""
        url = f"{self._settings.ai_engine_url}/webhooks/v2/score/post"
        headers = {"X-AI-API-Key": self._settings.ai_engine_api_key}
        payload = {
            "user_id": str(user_id),
            "post_id": str(post_id),
            "draft_text": draft_text,
            "top_posts_sample": top_posts_sample,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("virality_score_engine_call_failed", error=str(e))
            return None
