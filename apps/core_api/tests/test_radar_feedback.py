"""Tests for the LLMOps Feedback Flywheel integration."""

import pytest
from uuid import uuid4

from app.dependencies import get_current_user, get_db
from app.models.user import User

@pytest.mark.asyncio
async def test_capture_comment_feedback(app, client):
    """Test that editing an AI draft successfully calculates similarity and returns 200."""
    
    # Create a real test user to satisfy PostgreSQL foreign key constraints
    test_user = None
    async for db in get_db():
        # Clean up any existing user to prevent unique constraints during re-runs
        from sqlalchemy import delete
        await db.execute(delete(User).where(User.email == "test_flywheel@example.com"))
        
        test_user = User(
            email="test_flywheel@example.com",
            full_name="Flywheel Tester",
            linkedin_id="li_test_999"
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        break
        
    if not test_user:
        pytest.fail("Database connection failed")
        
    # Override authentication dependency to simulate a logged-in human
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    payload = {
        "post_id": "test-post-123",
        "original_generated_comment": "Absolutely brilliant piece on Python architectures!",
        "final_user_edited_comment": "Absolutely brilliant piece on Python architectures! Though, I prefer Golang.",
        "was_used": True,
        "engagement_likes": 0,
        "engagement_replies": 0
    }
    
    response = await client.post("/api/v1/comments/feedback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Feedback captured" in data["message"]
    
    # Clean up override
    app.dependency_overrides.clear()
