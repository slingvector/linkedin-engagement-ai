"""
UserSettings model — stores per-user content preferences and brand kit.
Used by CarouselService (brand colors/font/logo) and future personalization.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """
    user_settings table — one row per user.
    Brand kit is used by the Carousel Renderer microservice.
    Posting preferences feed Smart Fill defaults.
    """

    __tablename__ = "user_settings"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Brand Kit ─────────────────────────────────────────────────────────────
    primary_color = Column(
        String(7),
        nullable=True,
        default="#0A66C2",
        comment="Hex color used as carousel card background accent (#rrggbb)",
    )
    logo_url = Column(
        Text,
        nullable=True,
        comment="URL of user/company logo used on carousel slides",
    )
    font_family = Column(
        String(100),
        nullable=True,
        default="Inter",
        comment="Google Font name for carousel text rendering",
    )
    author_name = Column(
        String(200),
        nullable=True,
        comment="Display name shown on carousel footer",
    )
    author_tagline = Column(
        String(300),
        nullable=True,
        comment="One-line tagline under name on carousel footer",
    )

    # ── Posting Preferences ───────────────────────────────────────────────────
    pillars = Column(
        JSONB,
        nullable=True,
        default=list,
        comment="Saved content pillars for Smart Fill",
    )
    posts_per_week = Column(Integer, nullable=True, default=3)
    preferred_formats = Column(
        JSONB,
        nullable=True,
        default=list,
        comment='["text","carousel","video"]',
    )

    # ── Feature Flags ─────────────────────────────────────────────────────────
    auto_score_drafts = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Auto virality-score posts on creation",
    )
