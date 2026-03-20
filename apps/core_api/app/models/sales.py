import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # LinkedIn Data
    linkedin_url = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    headline = Column(String(500), nullable=True)
    company = Column(String(255), nullable=True)
    
    # AI Engine Enrichment
    intent_score = Column(Integer, nullable=False, default=0) # 0-100 score of how likely they are a buyer
    buying_signal = Column(Text, nullable=True) # E.g., "Asked about pricing on a competitor post"
    
    # Metadata
    avatar_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    user = relationship("User", back_populates="prospects")
    conversations = relationship("Conversation", back_populates="prospect", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # CRM State
    status = Column(String(50), nullable=False, default="new_lead") # new_lead, dm_initiated, demo_booked, closed_won, rejected
    
    # Message Context
    initial_message_draft = Column(Text, nullable=True)
    last_interaction_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    prospect = relationship("Prospect", back_populates="conversations")
