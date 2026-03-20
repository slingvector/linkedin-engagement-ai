import asyncio
import random
from uuid import uuid4
from datetime import datetime, timedelta
import structlog

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import _async_session
from app.models.post import Post
from app.models.analytics import PostMetrics, Engager
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService

logger = structlog.get_logger()

# Dummy professional personas to mimic an active LinkedIn population
PROFESSIONAL_HEADLINES = [
    "Software Engineer at Google",
    "Founder / CEO at StartupX",
    "Marketing Director",
    "Product Designer",
    "Recruiter at TechTalent",
    "CTO specializing in AI",
    "University Student",
    "Account Executive at Salesforce"
]

async def poll_metrics_and_classifications():
    """
    Mock metrics fetcher simulating the 'Growth System'.
    Finds published posts, adds randomized numeric metrics, and records 'Engagers' who interacted.
    Then hands them off to the LLM to classify.
    """
    while True:
        try:
            async with _async_session() as db:
                # 1. Fetch published posts
                posts = await db.execute(select(Post).where(Post.status == "published"))
                posts = list(posts.scalars().all())

                if posts:
                    for post in posts:
                        # Add a bump to metrics
                        metrics = await db.execute(
                            select(PostMetrics).where(PostMetrics.post_id == post.id)
                        )
                        metric_entry = metrics.scalars().first()
                        
                        if not metric_entry:
                            metric_entry = PostMetrics(
                                post_id=post.id,
                                impressions=random.randint(10, 50),
                                likes=random.randint(1, 5),
                                comments=random.randint(0, 2),
                                shares=0,
                                recorded_at=datetime.utcnow() - timedelta(days=random.randint(0, 5)) 
                             )
                            db.add(metric_entry)
                        else:
                            metric_entry.impressions += random.randint(10, 50)
                            metric_entry.likes += random.randint(1, 5)

                        # Generate 1 to 2 brand new mock engagers per interval
                        for _ in range(random.randint(1, 2)):
                            e = Engager(
                                post_id=post.id,
                                linkedin_id=str(uuid4())[:8],
                                headline=random.choice(PROFESSIONAL_HEADLINES),
                                interaction_type=random.choice(["like", "comment"]),
                            )
                            db.add(e)
                    
                    await db.commit()

                # 2. Call the AI classification chunk processor
                analytics_service = AnalyticsService(AnalyticsRepository(db))
                await analytics_service.process_unclassified_engagers()

        except asyncio.CancelledError:
            logger.info("metrics_worker_cancelled")
            break
        except Exception as e:
            logger.error("metrics_worker_exception", error=str(e))
            
        await asyncio.sleep(20) # Poll every 20s
