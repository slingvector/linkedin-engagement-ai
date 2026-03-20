"""
Comment Draft repository.
"""

from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creator import CommentDraft


class CommentDraftRepository:
    """CRUD for AI-generated comment drafts."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, draft: CommentDraft) -> CommentDraft:
        """Save a new set of comment strategies from the AI Engine."""
        self._db.add(draft)
        await self._db.commit()
        await self._db.refresh(draft)
        return draft

    async def get_by_ingested_post(
        self, user_id: UUID, ingested_post_id: UUID
    ) -> CommentDraft | None:
        """Get the comment draft for a specific post in the feed."""
        result = await self._db.execute(
            select(CommentDraft).where(
                CommentDraft.user_id == user_id,
                CommentDraft.ingested_post_id == ingested_post_id,
                CommentDraft.deleted_at.is_(None),
            ).order_by(desc(CommentDraft.created_at))
        )
        return result.scalars().first()

    async def update(self, draft: CommentDraft) -> CommentDraft:
        """Update draft status (e.g., when copied)."""
        await self._db.commit()
        await self._db.refresh(draft)
        return draft
