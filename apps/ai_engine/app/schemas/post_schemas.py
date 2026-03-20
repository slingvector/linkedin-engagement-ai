"""
Pydantic schemas for post generation webhook.
Strict API contracts between Core API and AI Engine.
"""

from pydantic import BaseModel, Field


class PostGenerationRequest(BaseModel):
    """Inbound: What Core API sends to the AI Engine."""

    user_id: str = Field(..., description="UUID of the requesting user")
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
    user_preferences: dict | None = Field(
        default=None,
        description="User style rules from Data Flywheel (injected as few-shot context)",
    )


class PostGenerationResponse(BaseModel):
    """Outbound: Structured post returned to Core API / Frontend."""

    hook: str = Field(..., description="Attention-grabbing opening line")
    body_content: str = Field(..., description="Main body of the post")
    call_to_action: str = Field(..., description="Closing CTA to drive engagement")
