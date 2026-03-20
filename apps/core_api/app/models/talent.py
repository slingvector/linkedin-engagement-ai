from datetime import datetime
import uuid
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Requisition(Base):
    """
    Represents an open Job Role the recruiter is hiring for.
    """
    __tablename__ = "requisitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    title: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Candidate(Base):
    """
    Represents an inbound/discovered Talent Profile mapped against a specific user's ATS.
    """
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    name: Mapped[str] = mapped_column(String)
    headline: Mapped[str] = mapped_column(String)
    current_role: Mapped[str] = mapped_column(String)
    current_company: Mapped[str] = mapped_column(String, nullable=True)
    skills: Mapped[str] = mapped_column(Text, nullable=True) # JSON or CSV describing skills
    
    # State flags mapped over to the Kanban
    ats_status: Mapped[str] = mapped_column(String, default="sourced") # sourced, outreached, interviewing, hired, rejected
    match_score: Mapped[int] = mapped_column(Integer, default=0) # 0-100 calculated by AI Copilot
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
