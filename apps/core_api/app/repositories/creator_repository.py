"""
Creator repository — data access for TrackedCreators and IngestedPosts.
"""

from uuid import UUID

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creator import TrackedCreator, IngestedPost


class CreatorRepository:
    """Handles Creator Radar CRUD and ingested post management."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # --- Tracked Creators ---

    async def add_tracked_creator(self, creator: TrackedCreator) -> TrackedCreator:
        """Add a new creator to monitor."""
        self._db.add(creator)
        await self._db.commit()
        await self._db.refresh(creator)
        return creator

    async def get_tracked_creator(self, creator_id: UUID, user_id: UUID) -> TrackedCreator | None:
        """Get a tracked creator by ID."""
        result = await self._db.execute(
            select(TrackedCreator).where(
                TrackedCreator.id == creator_id,
                TrackedCreator.user_id == user_id,
                TrackedCreator.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_tracked_creators(
        self, user_id: UUID, active_only: bool = True
    ) -> list[TrackedCreator]:
        """List all tracked creators for a user."""
        query = select(TrackedCreator).where(
            TrackedCreator.user_id == user_id,
            TrackedCreator.deleted_at.is_(None),
        )
        if active_only:
            query = query.where(TrackedCreator.is_active == 1)
        
        query = query.order_by(TrackedCreator.created_at)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def soft_delete_creator(self, creator: TrackedCreator) -> TrackedCreator:
        """Stop tracking a creator (soft delete)."""
        from datetime import datetime, timezone
        creator.deleted_at = datetime.now(timezone.utc)
        creator.is_active = 0
        await self._db.commit()
        await self._db.refresh(creator)
        return creator

    # --- Ingested Posts ---

    async def add_ingested_post(self, post: IngestedPost) -> IngestedPost | None:
        """Insert a scraped post from the IIE (Network Interceptor)."""
        # Note: IIE ingestion logic would usually run in a background worker,
        # but the API allows inserting results here.
        self._db.add(post)
        await self._db.commit()
        await self._db.refresh(post)
        return post

    async def get_ingested_post(self, post_id: UUID) -> IngestedPost | None:
        """Get a specific ingested post."""
        result = await self._db.execute(
            select(IngestedPost).where(
                IngestedPost.id == post_id,
                IngestedPost.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_feed(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict], int]:
        """
        The "Comment Action Desk" feed.
        Returns IngestedPosts joined with their TrackedCreator name, 
        ordered by most recently posted.
        """
        # This requires a JOIN to ensure the user actually tracks this creator
        query = (
            select(IngestedPost, TrackedCreator.full_name, TrackedCreator.profile_picture_url)
            .join(TrackedCreator, IngestedPost.tracked_creator_id == TrackedCreator.id)
            .where(
                TrackedCreator.user_id == user_id,
                TrackedCreator.is_active == 1,
                TrackedCreator.deleted_at.is_(None),
                IngestedPost.deleted_at.is_(None),
            )
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one()

        # Fetch page
        query = query.order_by(desc(IngestedPost.posted_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(query)
        
        # Format as list of dicts for the response
        feed = []
        for post, creator_name, creator_pic in result:
            feed.append({
                "post": post,
                "creator_name": creator_name,
                "creator_picture": creator_pic
            })
            
        return feed, total
