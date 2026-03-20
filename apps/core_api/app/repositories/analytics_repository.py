from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.analytics import PostMetrics, Engager, EngagerClassification


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics_timeline(self, user_id: UUID) -> list[PostMetrics]:
        """
        Fetch time-series metrics data joined across all published posts for a user.
        In a real scenario, this would group by date.
        """
        # For our mock implementation, just get all PostMetrics joined to Post where Post.user_id == user_id
        # We will keep it simple and just load all PostMetrics for now.
        from app.models.post import Post

        result = await self.db.execute(
            select(PostMetrics)
            .join(Post, Post.id == PostMetrics.post_id)
            .where(Post.user_id == user_id)
            .order_by(PostMetrics.recorded_at.asc())
        )
        return list(result.scalars().all())

    async def get_audience_demographics(self, user_id: UUID) -> dict[str, int]:
        """
        Returns a grouped count of Personas from the EngagerClassifications
        for posts belonging to this exact user.
        """
        from app.models.post import Post

        result = await self.db.execute(
            select(
                EngagerClassification.persona, 
                func.count(EngagerClassification.id)
            )
            .join(Engager, Engager.id == EngagerClassification.engager_id)
            .join(Post, Post.id == Engager.post_id)
            .where(Post.user_id == user_id)
            .group_by(EngagerClassification.persona)
        )
        
        return {row[0]: row[1] for row in result.all()}

    async def get_unclassified_engagers(self, limit: int = 50) -> list[Engager]:
        """
        Find engagers that do not yet have an assigned Classification.
        """
        result = await self.db.execute(
            select(Engager)
            .outerjoin(EngagerClassification, Engager.id == EngagerClassification.engager_id)
            .where(EngagerClassification.id == None)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_classification(self, engager_id: UUID, persona: str) -> EngagerClassification:
        classification = EngagerClassification(engager_id=engager_id, persona=persona)
        self.db.add(classification)
        await self.db.commit()
        await self.db.refresh(classification)
        return classification
