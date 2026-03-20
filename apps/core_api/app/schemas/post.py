"""
Pydantic request/response schemas for post generation and CRUD.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class IdeaGenerateRequest(BaseModel):
    """Frontend request to generate 5 ideas via AI."""
    target_audience: str = Field(..., max_length=100, description="Target audience")
    topic_niche: str = Field(..., max_length=100, description="Niche topic area")


class IdeaResponseItem(BaseModel):
    idea: str
    angle: str


class IdeaGenerateResponse(BaseModel):
    items: list[IdeaResponseItem]


class PostGenerateRequest(BaseModel):
    """Frontend request to generate a new post via AI."""

    topic: str = Field(..., max_length=200, description="Topic for the post")
    audience: str = Field(..., max_length=100, description="Target audience")
    framework: str = Field(
        ...,
        description="Content framework: story, contrarian, playbook, or lessons",
    )
    tone: str | None = Field(
        default="professional_but_conversational",
        max_length=100,
    )


class PostResponse(BaseModel):
    """Full post response returned to frontend."""

    id: str
    hook: str
    body_content: str
    call_to_action: str
    final_content: str | None = None
    status: str = "draft"
    topic: str
    audience: str
    framework: str
    tone: str | None = None
    likes: int = 0
    comments_count: int = 0
    impressions: int = 0
    created_at: datetime
    scheduled_at: datetime | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class PostUpdateRequest(BaseModel):
    """Update a post draft (e.g., after user edits)."""

    hook: str | None = None
    body_content: str | None = None
    call_to_action: str | None = None
    final_content: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class PostScheduleRequest(BaseModel):
    """Update a post to scheduled status with a target time."""
    scheduled_at: datetime


class PostListResponse(BaseModel):
    """Paginated list of posts."""

    posts: list[PostResponse]
    total: int
    page: int
    per_page: int
