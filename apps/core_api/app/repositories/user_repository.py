"""
User repository — data access layer.
Handles all database operations for users.
Follows Repository Pattern (SRP: only data access, no business logic).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user by their UUID primary key."""
        result = await self._db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_linkedin_id(self, linkedin_id: str) -> User | None:
        """Fetch a user by their LinkedIn ID."""
        result = await self._db.execute(
            select(User).where(User.linkedin_id == linkedin_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email."""
        result = await self._db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Insert a new user record."""
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Persist changes to an existing user record."""
        await self._db.commit()
        await self._db.refresh(user)
        return user
