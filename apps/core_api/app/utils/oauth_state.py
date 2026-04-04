"""
OAuth CSRF state helpers — Postgres-backed, restart-safe, multi-worker-safe.

Replaces the in-memory _oauth_states dicts in the auth controllers.
States are automatically expired after 10 minutes.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_state import OAuthState

_STATE_TTL_MINUTES = 10


async def create_oauth_state(db: AsyncSession, *, user_id: str | None = None) -> str:
    """
    Generate a cryptographically secure state token and persist it.

    Args:
        db: Database session.
        user_id: For write-flow OAuth (user is already authed). None for read-flow.

    Returns:
        The state token string to embed in the OAuth redirect URL.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES)

    state = OAuthState(state_token=token, user_id=user_id, expires_at=expires_at)
    db.add(state)
    await db.commit()
    return token


async def consume_oauth_state(db: AsyncSession, state: str) -> str | None:
    """
    Validate and atomically consume a state token.

    Deletes the token regardless of whether it's valid (prevents replay attacks).

    Args:
        db: Database session.
        state: The state token from the OAuth callback query param.

    Returns:
        The associated user_id (may be None for read-flow), or raises LookupError
        if the token is missing or expired.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(OAuthState).where(
            OAuthState.state_token == state,
            OAuthState.expires_at > now,
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        # Also purge any expired tokens opportunistically
        await db.execute(delete(OAuthState).where(OAuthState.expires_at <= now))
        await db.commit()
        return "__invalid__"  # Sentinel — caller checks against this

    user_id = record.user_id
    await db.delete(record)
    await db.commit()
    return user_id  # None for read-flow, str UUID for write-flow


_INVALID_SENTINEL = "__invalid__"
