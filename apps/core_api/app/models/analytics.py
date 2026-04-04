import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class PostMetrics(Base):
    """
    Daily snapshot of performance for a published post.
    """
    __tablename__ = "post_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    
    impressions = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Engager(Base):
    """
    A specific LinkedIn ID/Profile that interacted with a post.
    """
    __tablename__ = "engagers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    
    linkedin_id = Column(String, nullable=False) # Extracted network ID
    headline = Column(String, nullable=False)
    interaction_type = Column(String, nullable=False) # 'like', 'comment'
    
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    classification = relationship("EngagerClassification", back_populates="engager", uselist=False, cascade="all, delete-orphan")


class EngagerClassification(Base):
    """
    An AI-derived structural class based on an engager's headline.
    """
    __tablename__ = "engager_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engager_id = Column(UUID(as_uuid=True), ForeignKey("engagers.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    persona = Column(String, nullable=False) # 'Founder / C-Suite', 'Engineering & Tech', etc.
    
    classified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    engager = relationship("Engager", back_populates="classification")
