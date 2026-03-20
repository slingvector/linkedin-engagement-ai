from datetime import datetime
import uuid
from sqlalchemy import String, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class ShadowActionLog(Base):
    """
    Logs the delta between what the AI generated and what the Human ultimately edited/approved.
    Used for Direct Preference Optimization (DPO) and future edge model fine-tuning.
    """
    __tablename__ = "shadow_action_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    action_type: Mapped[str] = mapped_column(String) # e.g. "post_generation", "dm_draft", "comment_reply"
    
    ai_draft_content: Mapped[str] = mapped_column(Text)
    human_final_content: Mapped[str] = mapped_column(Text)
    
    # Simple edit distance metric (e.g., Levenshtein percentage) 1.0 = no changes, 0.0 = completely rewritten
    edit_similarity_score: Mapped[float] = mapped_column(Float, nullable=True)
    
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LLMEvaluation(Base):
    """
    Automated LLM-as-a-Judge scores grading historical platform output across safety and quality metrics.
    """
    __tablename__ = "llm_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    log_id: Mapped[str] = mapped_column(String, ForeignKey("shadow_action_logs.id"), index=True)
    
    # Scores 1-100
    hallucination_score: Mapped[int] = mapped_column(Integer)
    tone_adherence_score: Mapped[int] = mapped_column(Integer)
    safety_compliance_score: Mapped[int] = mapped_column(Integer)
    
    judge_rationale: Mapped[str] = mapped_column(Text)
    
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
