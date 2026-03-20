import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings
from app.models.base import Base

# Imports force metadata registration
from app.models import (
    User, Post, TrackedCreator, IngestedPost, CommentDraft,
    PostMetrics, Engager, EngagerClassification, Job, Resume, Application,
    Prospect, Conversation, Candidate, Requisition, TargetAccount,
    CompanySignal, Campaign, SequenceStep, ShadowActionLog, LLMEvaluation
)

async def init_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Master Database initialized successfully with all tables!")

if __name__ == "__main__":
    asyncio.run(init_db())
