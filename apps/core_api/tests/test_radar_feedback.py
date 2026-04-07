"""Tests for the LLMOps Feedback Flywheel integration."""

import pytest
from sqlalchemy import delete, select

from app.dependencies import get_current_user, get_db
from app.models.llmops import ShadowActionLog
from app.models.user import User


async def _cleanup_test_user(email: str) -> None:
    """
    Delete the test user and all FK-linked rows.
    Order matters: child rows (shadow_action_logs) must be deleted before the user.
    This handles the case where ON DELETE CASCADE hasn't been applied to the live DB yet.
    """
    async for db in get_db():
        # Find the user (if they exist)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # Delete child rows first to satisfy FK constraint
            await db.execute(
                delete(ShadowActionLog).where(ShadowActionLog.user_id == user.id)
            )
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()
        break


@pytest.mark.asyncio
async def test_capture_comment_feedback(app, client):
    """Test that editing an AI draft successfully calculates similarity and returns 200."""

    # Ensure clean state before test (handles leftover rows from previous failed runs)
    await _cleanup_test_user("test_flywheel@example.com")

    # Create test user
    test_user = None
    async for db in get_db():
        test_user = User(
            email="test_flywheel@example.com",
            full_name="Flywheel Tester",
            linkedin_id="li_test_999",
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        break

    if not test_user:
        pytest.fail("Database connection failed")

    # Override authentication dependency to simulate a logged-in user
    app.dependency_overrides[get_current_user] = lambda: test_user

    payload = {
        "post_id": "test-post-123",
        "original_generated_comment": "Absolutely brilliant piece on Python architectures!",
        "final_user_edited_comment": "Absolutely brilliant piece on Python architectures! Though, I prefer Golang.",
        "was_used": True,
        "engagement_likes": 0,
        "engagement_replies": 0,
    }

    try:
        response = await client.post("/api/v1/comments/feedback", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Feedback captured" in data["message"]
    finally:
        # Always clean up after the test — child rows before user
        app.dependency_overrides.clear()
        await _cleanup_test_user("test_flywheel@example.com")
