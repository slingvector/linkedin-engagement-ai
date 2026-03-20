"""
Pydantic schemas for comment generation webhook.
"""

from pydantic import BaseModel, Field


class CommentGenerationRequest(BaseModel):
    """Inbound: Post content for comment generation."""

    user_id: str = Field(..., description="UUID of the requesting user")
    creator_name: str = Field(..., description="Name of the creator whose post this is")
    post_content: str = Field(..., description="The raw text of the scraped post")


class CommentGenerationResponse(BaseModel):
    """Outbound: Three comment strategies for the user to choose from."""

    comment_insightful: str = Field(
        ..., description="Adds genuine insight or a complementary data point"
    )
    comment_contrarian: str = Field(
        ..., description="Respectfully challenges or offers an alternative view"
    )
    comment_supportive: str = Field(
        ..., description="Builds on the point with personal experience"
    )
