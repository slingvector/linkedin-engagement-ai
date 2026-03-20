"""
Creator and Comment Service — business logic for Sprint 3.
Handles Creator CRUD and orchestrates AI Comment Generation.
"""

import time
from uuid import UUID

import httpx
import structlog

from app.config import get_settings, get_yaml_config
from app.models.creator import TrackedCreator, IngestedPost, CommentDraft
from app.repositories.creator_repository import CreatorRepository
from app.repositories.comment_repository import CommentDraftRepository
from app.schemas.creator import TrackedCreatorCreate, CommentGenerateRequest, CommentDraftUpdateRequest

logger = structlog.get_logger()


class CreatorService:
    """Business logic for Creator Radar and Comment Copilot."""

    def __init__(
        self,
        creator_repo: CreatorRepository,
        comment_repo: CommentDraftRepository,
    ):
        self._creator_repo = creator_repo
        self._comment_repo = comment_repo
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()

    # --- Creator Radar ---

    async def add_tracked_creator(
        self, user_id: UUID, req: TrackedCreatorCreate
    ) -> TrackedCreator:
        """Start tracking a new creator."""
        creator = TrackedCreator(
            user_id=user_id,
            linkedin_id=req.linkedin_id,
            profile_url=str(req.profile_url),
            full_name=req.full_name,
            headline=req.headline,
            profile_picture_url=str(req.profile_picture_url) if req.profile_picture_url else None,
            auto_generation_prompt=req.auto_generation_prompt,
            is_active=1,
        )
        return await self._creator_repo.add_tracked_creator(creator)

    async def list_tracked_creators(self, user_id: UUID) -> list[TrackedCreator]:
        """List active tracked creators."""
        return await self._creator_repo.list_tracked_creators(user_id)

    async def untrack_creator(self, creator_id: UUID, user_id: UUID) -> bool:
        """Stop tracking a creator (soft delete)."""
        creator = await self._creator_repo.get_tracked_creator(creator_id, user_id)
        if not creator:
            return False
        await self._creator_repo.soft_delete_creator(creator)
        return True

    # --- Comment Action Desk Feed ---

    async def get_action_desk_feed(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict], int]:
        """Get the feed of recent posts from tracked creators."""
        return await self._creator_repo.list_feed(user_id, page, per_page)


    # --- AI Comment Copilot ---

    async def generate_comments(
        self, user_id: UUID, req: CommentGenerateRequest
    ) -> CommentDraft:
        """
        Call the AI Engine to generate 3 comment strategies for a post.
        """
        # 1. Fetch the ingested post
        post = await self._creator_repo.get_ingested_post(req.ingested_post_id)
        if not post:
            raise ValueError("Ingested post not found")

        # 2. Fetch the creator metadata (need the name for the AI)
        creator = await self._creator_repo.get_tracked_creator(post.tracked_creator_id, user_id)
        if not creator:
            raise ValueError("Creator is not tracked by this user")

        ai_engine_url = self._settings.ai_engine_url
        ai_api_key = self._settings.ai_engine_api_key
        timeout = self._yaml_config.get("timeouts", {}).get("ai_engine_seconds", 15)

        # Build payload for AI Engine webhook
        payload = {
            "user_id": str(user_id),
            "creator_name": creator.full_name,
            "post_content": post.content,
        }

        logger.info(
            "ai_comment_call_started",
            user_id=str(user_id),
            ingested_post_id=str(post.id),
        )

        start_time = time.time()

        # Call AI Engine
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ai_engine_url}/webhooks/generate/comments",
                json=payload,
                headers={"X-AI-API-Key": ai_api_key},
            )
            response.raise_for_status()
            ai_result = response.json()

        latency_ms = round((time.time() - start_time) * 1000)

        logger.info(
            "ai_comment_call_complete",
            user_id=str(user_id),
            latency_ms=latency_ms,
        )

        # Create the draft
        draft = CommentDraft(
            user_id=user_id,
            ingested_post_id=post.id,
            insightful_content=ai_result["comment_insightful"],
            contrarian_content=ai_result["comment_contrarian"],
            supportive_content=ai_result["comment_supportive"],
            status="draft",
            generation_metadata={
                "latency_ms": latency_ms,
                "ai_engine_url": ai_engine_url,
            },
        )
        
        saved_draft = await self._comment_repo.create(draft)

        # Mark the post as processed
        post.is_processed = 1
        await self._creator_repo._db.commit()

        return saved_draft

    async def get_comment_draft(
        self, user_id: UUID, ingested_post_id: UUID
    ) -> CommentDraft | None:
        """Get the drafted comments for a specific post."""
        return await self._comment_repo.get_by_ingested_post(user_id, ingested_post_id)

    async def update_comment_draft(
        self, user_id: UUID, ingested_post_id: UUID, req: CommentDraftUpdateRequest
    ) -> CommentDraft | None:
        """Update a draft (e.g., when the user selects 'Copy & Go')."""
        draft = await self._comment_repo.get_by_ingested_post(user_id, ingested_post_id)
        if not draft:
            return None

        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(draft, field, value)

        return await self._comment_repo.update(draft)
