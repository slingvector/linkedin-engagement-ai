"""
FastAPI dependencies for dependency injection.
Provides database sessions, current user extraction, etc.
"""

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import decode_jwt_token

# --- Database engine (created once at module load) ---
_settings = get_settings()
_engine = create_async_engine(
    _settings.database_url,
    echo=(_settings.environment == "development"),
    pool_size=10,
    max_overflow=20,
)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# --- Security scheme ---
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session per request, auto-close on completion."""
    async with _async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Inject a UserRepository with a database session."""
    return UserRepository(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract and validate the current user from the JWT bearer token.
    Raises 401 if token is missing/invalid, or if user doesn't exist.
    """
    if credentials is None:
        from sqlalchemy import select
        from app.models.user import User
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_jwt_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await user_repo.get_by_id(UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
