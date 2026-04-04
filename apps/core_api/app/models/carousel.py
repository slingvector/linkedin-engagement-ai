"""
CarouselAsset model — stores AI-generated carousel slide outlines
and the rendered PDF artifact for a LinkedIn post.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class CarouselAsset(Base, UUIDMixin, TimestampMixin):
    """
    carousel_assets table.

    One CarouselAsset per carousel generation attempt on a Post.
    status lifecycle: draft → rendered → published
    """

    __tablename__ = "carousel_assets"

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # AI-generated 7-slide outline
    slides_json = Column(
        JSONB,
        nullable=False,
        comment="[{slide_number, headline, body, visual_suggestion}]",
    )

    # Rendered PDF artifact
    pdf_url = Column(
        Text,
        nullable=True,
        comment="GCS/local URL of rendered PDF",
    )

    slide_count = Column(Integer, default=7, nullable=False)

    status = Column(
        String(50),
        default="draft",
        nullable=False,
        comment="draft | rendered | published",
    )

    # Returned after LinkedIn Document Upload API (3-step flow)
    linkedin_asset_urn = Column(
        Text,
        nullable=True,
        comment="urn:li:document:... — returned by LinkedIn after upload",
    )

    # Brand kit used for rendering (snapshot to ensure reproducibility)
    brand_kit_snapshot = Column(
        JSONB,
        nullable=True,
        comment="Snapshot of brand_kit at render time: {primary_color, logo_url, font}",
    )
