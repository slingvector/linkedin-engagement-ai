"""
Publishing Worker — background loop that simulates publishing scheduled posts.
Scans for posts with status='scheduled' and scheduled_at <= now,
marks them as published.
"""

import asyncio
from datetime import datetime, timezone
import structlog
from sqlalchemy import select, update
from app.config import get_settings
from app.dependencies import _async_session
from app.models.post import Post

logger = structlog.get_logger()


async def publishing_scheduler_loop() -> None:
    """
    Background worker that runs alongside FastAPI.
    Finds posts due for publishing and acts on them.
    In Phase 2, this simulates LinkedIn API publishing.
    """
    settings = get_settings()

    logger.info(
        "worker_started",
        worker="publishing_scheduler_loop",
        env=settings.environment,
    )

    while True:
        try:
            # Wake up every 10 seconds to check schedule
            await asyncio.sleep(10)

            async with _async_session() as session:
                now = datetime.now(timezone.utc).replace(tzinfo=None) # naive UTC to match SQLAlchemy defaults

                # Select posts that are scheduled and due
                stmt = select(Post).where(
                    Post.status == "scheduled",
                    Post.scheduled_at <= now
                )
                result = await session.execute(stmt)
                due_posts = result.scalars().all()

                if due_posts:
                    post_ids = [p.id for p in due_posts]
                    logger.info("processing_scheduled_posts", count=len(due_posts), post_ids=[str(pid) for pid in post_ids])

                    # Mark them as published
                    update_stmt = (
                        update(Post)
                        .where(Post.id.in_(post_ids))
                        .values(status="published", published_at=now)
                    )
                    await session.execute(update_stmt)
                    await session.commit()

                    logger.info("scheduled_posts_published", count=len(due_posts))

        except asyncio.CancelledError:
            logger.info("worker_cancelled", worker="publishing_scheduler_loop")
            break
        except Exception as e:
            logger.error(
                "worker_error",
                worker="publishing_scheduler_loop",
                error=str(e),
                exc_info=True,
            )
            # Sleep backoff before retrying
            await asyncio.sleep(15)
