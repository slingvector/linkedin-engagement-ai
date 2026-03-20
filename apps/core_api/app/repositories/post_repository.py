"""
Post repository — data access layer for posts.
Handles all CRUD operations for post drafts.
"""

from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post


class PostRepository:
    """Repository for Post CRUD operations."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, post: Post) -> Post:
        """Insert a new post record."""
        self._db.add(post)
        await self._db.commit()
        await self._db.refresh(post)
        return post

    async def get_by_id(self, post_id: UUID, user_id: UUID) -> Post | None:
        """Fetch a post by ID, scoped to the user."""
        result = await self._db.execute(
            select(Post).where(
                Post.id == post_id,
                Post.user_id == user_id,
                Post.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list[Post], int]:
        """
        List posts for a user with pagination.
        Returns (posts, total_count).
        """
        query = select(Post).where(
            Post.user_id == user_id,
            Post.deleted_at.is_(None),
        )

        if status:
            query = query.where(Post.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one()

        # Fetch page
        query = query.order_by(desc(Post.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(query)
        posts = list(result.scalars().all())

        return posts, total

    async def update(self, post: Post) -> Post:
        """Persist changes to an existing post."""
        await self._db.commit()
        await self._db.refresh(post)
        return post

    async def soft_delete(self, post: Post) -> Post:
        """Soft-delete a post by setting deleted_at."""
        from datetime import datetime, timezone
        post.deleted_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(post)
        return post
