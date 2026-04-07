import asyncio
import os
import time
import structlog
import httpx
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any

from read_flow import ReadFlow, StorageProtocol

from app.dependencies import _async_session as AsyncSessionLocal
from sqlalchemy import select
from app.models.user import User
from app.models.creator import IngestedPost, TrackedCreator
from app.repositories.creator_repository import CreatorRepository
from app.config import get_settings

logger = structlog.get_logger()


def send_alert(message: str) -> None:
    """Send a Telegram alert. Silently skips if not configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"🚨 LinkedIn Ingestion\n{message}"},
            timeout=5,
        )
    except Exception:
        pass  # Never let alerting crash the worker

class PostgresStorageAdapter(StorageProtocol):
    """
    Implements StorageProtocol for linkedin_read_flow,
    mapping the normalized dicts into our Postgres schema.
    Since linkedin_read_flow is synchronous, we use a single persistent event loop.
    """
    
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def save_post(self, post: dict[str, Any]) -> bool:
        """
        Receives exactly this dict:
        {
            "url": "https://...",
            "post_urn": "urn:li:activity:...",
            "author_name": "...",
            "author_profile": "...",
            "content": "...",
            "hashtags": [...],
            "source": "..."
        }
        """
        return self.loop.run_until_complete(self._async_save_post(post))
        
    def post_exists(self, url: str) -> bool:
        return self.loop.run_until_complete(self._async_post_exists(url))
        
    def get_all_urls(self) -> set[str]:
        return self.loop.run_until_complete(self._async_get_all_urls())

    async def _async_save_post(self, post: dict[str, Any]) -> bool:
        async with AsyncSessionLocal() as db:
            # Admin user required for ownership in our current schema
            result = await db.execute(select(User).limit(1))
            admin = result.scalars().first()
            if not admin:
                logger.error("postgres_adapter: no admin user found in db.")
                return False
            
            # Deduplication logic upfront
            existing = await db.execute(
                select(IngestedPost).where(IngestedPost.linkedin_post_id == post.get("post_urn", ""))
            )
            if existing.scalars().first():
                return False

            repo = CreatorRepository(db)
            profile_url = post.get("author_profile", "")
            author_name = post.get("author_name", "Unknown")
            
            linkedin_id = ""
            slug_match = profile_url.split("/in/")
            if len(slug_match) > 1:
                linkedin_id = slug_match[1].strip("/")
            else:
                linkedin_id = f"discovered-{uuid4().hex[:8]}"

            try:
                creator_result = await db.execute(select(TrackedCreator).where(TrackedCreator.linkedin_id == linkedin_id, TrackedCreator.user_id == admin.id).limit(1))
                creator = creator_result.scalars().first()
                
                if not creator:
                    new_creator = TrackedCreator(
                        user_id=admin.id,
                        profile_url=profile_url,
                        linkedin_id=linkedin_id,
                        full_name=author_name
                    )
                    creator = await repo.add_tracked_creator(new_creator)

                media_val = post.get("media_urls", [])
                content_val = post.get("content", "")
                if media_val:
                    content_val += "\n\n[Media Attached]\n" + "\n".join(media_val)

                ingested = IngestedPost(
                    tracked_creator_id=creator.id,
                    linkedin_post_id=post.get("post_urn", ""),
                    post_url=post.get("url", ""),
                    content=content_val[:800],
                    posted_at=datetime.now(timezone.utc),
                    likes=post.get("likes", 0),
                    comments=post.get("comments", 0),
                    ingestion_source="bulk_read_flow"
                )
                await repo.add_ingested_post(ingested)
                return True
            except Exception as e:
                logger.error("postgres_adapter: failed to save post", error=str(e), urn=post.get("post_urn"))
                return False

    async def _async_post_exists(self, url: str) -> bool:
        async with AsyncSessionLocal() as db:
             existing = await db.execute(
                 select(IngestedPost).where(IngestedPost.post_url == url)
             )
             return existing.scalars().first() is not None

    async def _async_get_all_urls(self) -> set[str]:
        async with AsyncSessionLocal() as db:
             existing = await db.execute(select(IngestedPost.post_url))
             urls = existing.scalars().all()
             return set(urls)


def run_bulk_ingestion():
    import os
    settings = get_settings()
    logger.info("bulk_ingestion_starting", mode="trial-run")
    
    # Since the library dynamically reads LINKEDIN_LI_AT, LINKEDIN_EMAIL, and LINKEDIN_PASSWORD
    # directly from the environment, we map our namespaced read account variables into os.environ
    if settings.linkedin_read_li_at:
        os.environ["LINKEDIN_LI_AT"] = settings.linkedin_read_li_at
    if settings.linkedin_read_email:
        os.environ["LINKEDIN_EMAIL"] = settings.linkedin_read_email
    if settings.linkedin_read_password:
        os.environ["LINKEDIN_PASSWORD"] = settings.linkedin_read_password

    try:
        flow = ReadFlow(storage=PostgresStorageAdapter())
    except SystemExit as e:
        msg = str(e)
        logger.error("read_flow_auth_failed", error=msg)
        if "CAPTCHA" in msg or "2FA" in msg or "challenge" in msg.lower():
            send_alert("⚠️ LinkedIn CAPTCHA/2FA triggered.\nLog in manually, solve the challenge, then update li_at in .env and restart.")
        else:
            send_alert(f"❌ LinkedIn auth failed at startup.\nCheck LINKEDIN_READ_LI_AT / EMAIL / PASSWORD in .env.\n\n{msg}")
            
        logger.info("bulk_ingestion_paused_due_to_auth")
        # Prevent tight restart loops that could softly ban the account
        time.sleep(3600)
        return

    # Trial Run: Fetch own feed periodically
    while True:
        try:
            logger.info("bulk_ingestion_fetching_feed")
            result = flow.fetch_feed()
            
            if result.get("success"):
                logger.info("bulk_ingestion_feed_success",
                            fetched=result.get("fetched"),
                            saved=result.get("saved"),
                            skipped_duplicate=result.get("skipped_duplicate"))
            else:
                error = result.get("error", "unknown")
                logger.error("bulk_ingestion_feed_failed", error=error)
                send_alert(f"❌ LinkedIn feed fetch failed.\nError: {error}")

        except Exception as e:
            logger.exception("bulk_ingestion_loop_error", exc_info=e)
            send_alert(f"💥 Ingestion worker crashed.\n{type(e).__name__}: {e}")
            
        logger.info("bulk_ingestion_sleeping", interval=3600)
        time.sleep(3600)

if __name__ == "__main__":
    run_bulk_ingestion()
