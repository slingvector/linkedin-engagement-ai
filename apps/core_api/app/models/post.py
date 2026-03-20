"""
Post model — stores generated LinkedIn post drafts.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, UUIDMixin, TimestampMixin


class Post(Base, UUIDMixin, TimestampMixin):
    """
    Posts table.

    Stores AI-generated LinkedIn post drafts with their metadata.
    status tracks the post lifecycle: draft → approved → published → archived.
    generation_metadata captures the AI params used for observability / Data Flywheel.
    """

    __tablename__ = "posts"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Post content (structured output from AI Engine)
    hook = Column(Text, nullable=False)
    body_content = Column(Text, nullable=False)
    call_to_action = Column(Text, nullable=False)

    # User-editable final version (tracks edits for Data Flywheel)
    final_content = Column(Text, nullable=True, comment="User-edited merged content")

    # Post lifecycle
    status = Column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
        comment="draft | approved | published | archived",
    )

    # Generation context (for Data Flywheel replay and observability)
    topic = Column(String(200), nullable=False)
    audience = Column(String(100), nullable=False)
    framework = Column(String(50), nullable=False)
    tone = Column(String(100), nullable=True)

    # Scheduling and lifecycle metadata
    scheduled_at = Column(DateTime, nullable=True, comment="When this should be auto-published")
    published_at = Column(DateTime, nullable=True, comment="When this was published or simulated published")

    # AI observability metadata
    generation_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="LLM model, tokens used, latency, prompt version",
    )

    # Engagement metrics (populated post-publish via ingestion)
    likes = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
