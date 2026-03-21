import asyncio
import structlog
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings
from app.models.base import Base

# Imports force metadata registration
from app.models import (
    User, Post, TrackedCreator, IngestedPost, CommentDraft,
    PostMetrics, Engager, EngagerClassification, Job, Resume, Application,
    Prospect, Conversation, Candidate, Requisition, TargetAccount,
    CompanySignal, Campaign, SequenceStep, ShadowActionLog, LLMEvaluation,
    CommentFeedback
)

logger = structlog.get_logger()

async def reset_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    
    logger.info("Dropping all tables from the database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Re-creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Master Database reset successfully! Clean slate achieved.")

if __name__ == "__main__":
    asyncio.run(reset_db())
