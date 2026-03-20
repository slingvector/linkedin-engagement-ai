"""
Pydantic schemas for user data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Public user profile response."""
    id: str
    email: str
    full_name: str | None = None
    profile_picture_url: str | None = None
    subscription_tier: str = "free"
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPreferencesUpdate(BaseModel):
    """Partial update for user preferences (Data Flywheel)."""
    preferences: dict = Field(
        ...,
        description="AI style rules learned from user behavior",
    )
