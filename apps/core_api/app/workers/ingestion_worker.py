"""
Safe Post Ingestion Worker.
Simulates the Tier 1 Network Interceptor (IIE) to populate the Action Desk feed.
In production, this reads from a Redis queue populated by Playwright.
For Phase 1, it runs periodically to inject mock posts for active creators.
"""

import asyncio
import random
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import structlog

from app.dependencies import get_db
from app.repositories.creator_repository import CreatorRepository
from app.models.creator import IngestedPost

logger = structlog.get_logger()

# Mock topics to simulate real LinkedIn posts
MOCK_TOPICS = [
    "Just wrapped up an incredible quarter. The secret? Shipping standard features fast, and innovating only where it creates a moat.",
    "Unpopular opinion: You don't need a complex microservices architecture until you hit 100k DAU. A monolith is fine.",
    "Here are 3 lessons from scaling our sales team from 0 to 10 reps this year. First, hire for adaptability over pedigree...",
    "Why is everyone overcomplicating AI? The real value is in data pipelines, not the models themselves.",
    "If your SaaS churn is over 5% per month, you don't have a marketing problem. You have a product-market-fit problem.",
]

async def safe_ingest_mock_posts():
    """
    Periodically polls for active creators and injects mock posts.
    Runs as a background task.
    """
    logger.info("bg_worker_started", worker="safe_post_ingestion")
    
    while True:
        try:
            # We need a fresh session for the background task
            async for db in get_db():
                repo = CreatorRepository(db)
                
                # We need all active creators across all users.
                # Since list_tracked_creators requires a user_id right now,
                # we do a direct query for the worker.
                from sqlalchemy import select
                from app.models.creator import TrackedCreator
                
                result = await db.execute(
                    select(TrackedCreator).where(
                        TrackedCreator.is_active == 1,
                        TrackedCreator.deleted_at.is_(None)
                    )
                )
                active_creators = list(result.scalars().all())
                
                if active_creators:
                    logger.debug("ingestion_worker_polling", active_creators=len(active_creators))
                    
                    # Randomly decide to "discover" a new post (e.g., 20% chance per run)
                    for creator in active_creators:
                        if random.random() < 0.2:
                            post_urn = f"urn:li:share:{uuid4().hex[:12]}"
                            new_post = IngestedPost(
                                tracked_creator_id=creator.id,
                                linkedin_post_id=post_urn,
                                post_url=f"https://www.linkedin.com/feed/update/{post_urn}/",
                                content=random.choice(MOCK_TOPICS),
                                posted_at=datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 60)),
                                likes=random.randint(10, 500),
                                comments=random.randint(2, 50),
                            )
                            await repo.add_ingested_post(new_post)
                            logger.info(
                                "new_post_ingested", 
                                creator_id=str(creator.id),
                                post_id=str(new_post.id)
                            )
                            
            # Sleep for 60 seconds before polling again
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("bg_worker_stopped", worker="safe_post_ingestion")
            break
        except Exception as e:
            logger.error("bg_worker_error", worker="safe_post_ingestion", error=str(e))
            await asyncio.sleep(60)  # Sleep on error before retrying
