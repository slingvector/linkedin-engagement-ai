"""
Creator tracking models for the Creator Radar and Comment Copilot.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, UUIDMixin, TimestampMixin


class TrackedCreator(Base, UUIDMixin, TimestampMixin):
    """
    Creators the user is monitoring (Creator Radar).
    """

    __tablename__ = "tracked_creators"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    linkedin_id = Column(String, nullable=False)
    profile_url = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    headline = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    
    # Auto-comment strategy preferences for this specific creator
    auto_generation_prompt = Column(
        String, 
        nullable=True, 
        comment="Custom instructions for when this creator posts"
    )

    is_active = Column(Integer, default=1, nullable=False)


class IngestedPost(Base, UUIDMixin, TimestampMixin):
    """
    Posts scraped/ingested from Tracked Creators.
    """

    __tablename__ = "ingested_posts"

    tracked_creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracked_creators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    linkedin_post_id = Column(String, nullable=False, unique=True, index=True)
    post_url = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    posted_at = Column(DateTime, nullable=False, index=True)

    # Scraped engagement
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    reposts = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Number of reposts/reshares — populated by appium read flow or enrichment",
    )

    ingestion_source = Column(
        String(50),
        default="scheduled",
        comment="scheduled | direct | appium",
    )
    
    is_processed = Column(
        Integer, 
        default=0, 
        comment="1 if AI has generated comment drafts for this post"
    )


class CommentDraft(Base, UUIDMixin, TimestampMixin):
    """
    AI-generated comment drafts for a specific ingested post.
    """

    __tablename__ = "comment_drafts"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ingested_post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingested_posts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The 3 generated strategies
    insightful_content = Column(Text, nullable=False)
    contrarian_content = Column(Text, nullable=False)
    supportive_content = Column(Text, nullable=False)

    # The one the user selected (if any)
    selected_strategy = Column(
        String(50), 
        nullable=True, 
        comment="insightful | contrarian | supportive"
    )
    
    # The final edited text they copied/published
    final_content = Column(Text, nullable=True)

    status = Column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
        comment="draft | copied | published | archived",
    )

    # Telemetry for the Data Flywheel
    generation_metadata = Column(JSONB, default=dict, nullable=False)
