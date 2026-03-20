"""
Post service — business logic for post generation and management.
Orchestrates the Core API → AI Engine webhook call.
"""

import time
from uuid import UUID

import httpx
import structlog

from app.config import get_settings, get_yaml_config
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.schemas.post import (
    PostGenerateRequest, 
    PostUpdateRequest, 
    IdeaGenerateRequest, 
    IdeaGenerateResponse
)
from datetime import datetime

logger = structlog.get_logger()


class PostService:
    """
    Orchestrates post generation and CRUD.

    The generation flow:
    1. Frontend sends topic/audience/framework/tone
    2. This service calls the AI Engine webhook via HTTP
    3. AI Engine calls the LLM and returns structured JSON
    4. We save the result as a draft in Postgres
    5. User reviews/edits → publish (Sprint 3+)
    """

    def __init__(self, post_repository: PostRepository):
        self._post_repo = post_repository
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()

    async def generate_post(self, user_id: UUID, request: PostGenerateRequest) -> Post:
        """
        Generate a post by calling the AI Engine webhook.
        Enforces rate limits and timeouts per config.yaml.
        """
        ai_engine_url = self._settings.ai_engine_url
        ai_api_key = self._settings.ai_engine_api_key
        timeout = self._yaml_config.get("timeouts", {}).get("ai_engine_seconds", 15)

        # Build the webhook payload
        payload = {
            "user_id": str(user_id),
            "topic": request.topic,
            "audience": request.audience,
            "framework": request.framework,
            "tone": request.tone,
        }

        logger.info(
            "ai_engine_call_started",
            user_id=str(user_id),
            framework=request.framework,
        )

        start_time = time.time()

        # Call the AI Engine webhook
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ai_engine_url}/webhooks/generate/post",
                json=payload,
                headers={"X-AI-API-Key": ai_api_key},
            )
            response.raise_for_status()
            ai_result = response.json()

        latency_ms = round((time.time() - start_time) * 1000)

        logger.info(
            "ai_engine_call_complete",
            user_id=str(user_id),
            latency_ms=latency_ms,
        )

        # Save as a draft post
        post = Post(
            user_id=user_id,
            hook=ai_result["hook"],
            body_content=ai_result["body_content"],
            call_to_action=ai_result["call_to_action"],
            topic=request.topic,
            audience=request.audience,
            framework=request.framework,
            tone=request.tone,
            status="draft",
            generation_metadata={
                "latency_ms": latency_ms,
                "ai_engine_url": ai_engine_url,
            },
        )

        post = await self._post_repo.create(post)

        logger.info(
            "post_draft_created",
            user_id=str(user_id),
            post_id=str(post.id),
            framework=request.framework,
        )

        return post

    async def get_post(self, post_id: UUID, user_id: UUID) -> Post | None:
        """Get a single post by ID, scoped to user."""
        return await self._post_repo.get_by_id(post_id, user_id)

    async def list_posts(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list[Post], int]:
        """List user's posts with pagination."""
        return await self._post_repo.list_by_user(user_id, page, per_page, status)

    async def update_post(
        self, post_id: UUID, user_id: UUID, update: PostUpdateRequest
    ) -> Post | None:
        """Update a post draft (user edits content or changes status)."""
        post = await self._post_repo.get_by_id(post_id, user_id)
        if not post:
            return None

        # Apply partial updates
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(post, field, value)

        post = await self._post_repo.update(post)

        logger.info(
            "post_updated",
            post_id=str(post_id),
            user_id=str(user_id),
            fields=list(update_data.keys()),
        )

        return post

    async def schedule_post(
        self, post_id: UUID, user_id: UUID, scheduled_at: datetime
    ) -> Post | None:
        """Move a post to 'scheduled' state with an explicit date."""
        post = await self._post_repo.get_by_id(post_id, user_id)
        if not post:
            return None

        post.status = "scheduled"
        post.scheduled_at = scheduled_at
        post = await self._post_repo.update(post)
        logger.info("post_scheduled", post_id=str(post_id), scheduled_at=scheduled_at.isoformat())
        return post

    async def generate_ideas(self, user_id: UUID, request: IdeaGenerateRequest) -> IdeaGenerateResponse:
        """
        Proxies idea generation to the AI Engine.
        """
        ai_engine_url = self._settings.ai_engine_url
        ai_api_key = self._settings.ai_engine_api_key
        timeout = self._yaml_config.get("timeouts", {}).get("ai_engine_seconds", 15)

        payload = {
            "user_id": str(user_id),
            "target_audience": request.target_audience,
            "topic_niche": request.topic_niche,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ai_engine_url}/webhooks/generate/ideas",
                json=payload,
                headers={"X-AI-API-Key": ai_api_key},
            )
            response.raise_for_status()
            ai_result = response.json()

        return IdeaGenerateResponse(**ai_result)

    async def delete_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Soft-delete a post."""
        post = await self._post_repo.get_by_id(post_id, user_id)
        if not post:
            return False

        await self._post_repo.soft_delete(post)
        logger.info("post_deleted", post_id=str(post_id), user_id=str(user_id))
        return True
