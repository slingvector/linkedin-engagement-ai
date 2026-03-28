"""
Appium Ingestion Worker — LinkedIn Read Flow.

Orchestrates the Appium/ADB-based LinkedIn feed ingestion loop:
  1. Start Appium session
  2. Navigate to LinkedIn home feed
  3. Scroll and collect post URLs
  4. Apply YAML-driven engagement filters
  5. Persist filtered URLs to IngestedPost table with source="appium"
  6. Sleep and repeat

Run standalone:
    cd apps/core_api
    python -m app.workers.appium_ingestion_worker

Config (config.yaml → appium_read_flow:):
    enabled: true
    scroll_count: 10
    loop_sleep_interval_seconds: 3600
    filters:
      min_reactions: 13
      min_comments: 5
      min_reposts: 3

NOTE (Phase 1 limitation):
  LinkedIn's mobile feed cards do not expose engagement counts in the XML
  accessibility tree. Phase 1 collects all URLs and records counts as 0.
  Engagement filtering will apply once Phase 2 enrichment (Voyager API or
  web metadata fetch) is added. A TODO marks the enrichment hook below.
"""

import asyncio
import logging
import re
import traceback
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.config import get_settings, get_yaml_config
from app.dependencies import get_db
from app.models.creator import IngestedPost, TrackedCreator
from app.repositories.creator_repository import CreatorRepository

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Engagement filter helpers
# ---------------------------------------------------------------------------

def passes_filters(
    reactions: int,
    comments: int,
    reposts: int,
    filter_cfg: dict,
) -> bool:
    """
    Apply YAML-configured engagement thresholds.

    All three must pass (AND logic). A count of 0 (unknown) is
    treated as passing in Phase 1 so URLs are not silently dropped.
    """
    min_reactions = filter_cfg.get("min_reactions", 13)
    min_comments = filter_cfg.get("min_comments", 5)
    min_reposts = filter_cfg.get("min_reposts", 3)

    # Phase 1: unknown counts (0) always pass — see module docstring
    reactions_ok = (reactions == 0) or (reactions >= min_reactions)
    comments_ok = (comments == 0) or (comments >= min_comments)
    reposts_ok = (reposts == 0) or (reposts >= min_reposts)

    return reactions_ok and comments_ok and reposts_ok


def extract_post_id_from_url(url: str) -> Optional[str]:
    """
    Extract the LinkedIn post URN / activity ID from a URL.

    Handles formats:
      https://www.linkedin.com/feed/update/urn:li:activity:7234567890123456789/
      https://www.linkedin.com/posts/username_some-slug-activityId-7234567890/
    """
    # Primary: feed/update/urn:li:activity:...
    m = re.search(r"(urn:li:activity:\d+|urn:li:fs_updateV2:[^/?]+)", url)
    if m:
        return m.group(1)

    # Secondary: numeric activity ID at end of posts URL
    m = re.search(r"activity-?(\d{15,})", url)
    if m:
        return f"urn:li:activity:{m.group(1)}"

    # Fallback: use full URL hash as unique key
    return f"appium-url-{hash(url) & 0xFFFFFFFF}"


# ---------------------------------------------------------------------------
# Enrichment hook (Phase 2 placeholder)
# ---------------------------------------------------------------------------

async def enrich_post_metadata(url: str, settings) -> dict:
    """
    TODO (Phase 2): Fetch engagement metadata for a post URL.

    Options:
      - Hit LinkedIn Voyager API with li_at cookie
      - Use Playwright to load the post page and parse reaction/comment counts
      - Use the existing ingestion_worker.py Voyager interceptor approach

    Returns dict with keys: reactions, comments, reposts (all int).
    Returns zeros for Phase 1 (no enrichment).
    """
    return {"reactions": 0, "comments": 0, "reposts": 0}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

async def persist_post_url(url: str, metadata: dict):
    """
    Persist a collected LinkedIn post URL to the ingested_posts table.

    Creates a stub TrackedCreator entry (profile unknown at this stage)
    that can be enriched in Phase 2 after metadata lookup.
    """
    post_id = extract_post_id_from_url(url)
    if not post_id:
        logger.warning("appium_worker_bad_url", url=url)
        return

    reactions = metadata.get("reactions", 0)
    comments = metadata.get("comments", 0)
    reposts = metadata.get("reposts", 0)

    async for db in get_db():
        repo = CreatorRepository(db)
        from sqlalchemy import select
        from app.models.user import User

        # Get first user (admin) as the owner
        result = await db.execute(select(User).limit(1))
        admin = result.scalars().first()
        if not admin:
            logger.error("appium_worker_no_admin_user")
            return

        try:
            # Upsert a stub creator — will be enriched when profile is known
            creator = await repo.add_tracked_creator(
                user_id=admin.id,
                profile_url="https://www.linkedin.com/in/unknown",
                linkedin_id=f"appium-discovery-{post_id[-8:]}",
                full_name="[Appium Discovery]",
            )

            ingested = IngestedPost(
                tracked_creator_id=creator.id,
                linkedin_post_id=post_id,
                post_url=url,
                content="",          # content unknown until Phase 2 enrichment
                posted_at=datetime.now(timezone.utc),
                likes=reactions,
                comments=comments,
                reposts=reposts,
                ingestion_source="appium",
                is_processed=0,
            )
            await repo.add_ingested_post(ingested)
            logger.info("appium_post_ingested", post_id=post_id, url=url[:80])

        except Exception as e:
            # Likely duplicate — unique constraint on linkedin_post_id
            logger.debug("appium_post_skip", post_id=post_id, reason=str(e))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

class AppiumIngestionWorker:
    """
    Encapsulates the LinkedIn Appium read-flow ingestion loop.
    Can be run as a module (`python -m app.workers.appium_ingestion_worker`)
    or imported and started as a background task in the FastAPI lifespan.
    """

    def __init__(self):
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()
        self._cfg = self._yaml_config.get("appium_read_flow", {})

    def _is_enabled(self) -> bool:
        return self._cfg.get("enabled", False)

    async def run(self):
        """
        Infinite ingestion loop. Exits only on unrecoverable errors or
        KeyboardInterrupt.
        """
        if not self._is_enabled():
            logger.info("appium_worker_disabled", hint="Set appium_read_flow.enabled=true in config.yaml")
            return

        logger.info("appium_ingestion_worker_start", config=self._cfg)

        # Import here to avoid mandatory Appium dependency at app boot time
        # (the service is only needed when the worker is actually running)
        from app.services.appium_read_service import AppiumReadService

        svc = AppiumReadService(config=self._cfg)
        filter_cfg = self._cfg.get("filters", {})
        scroll_count = self._cfg.get("scroll_count", 10)
        sleep_interval = self._cfg.get("loop_sleep_interval_seconds", 3600)

        while True:
            try:
                logger.info("appium_ingestion_cycle_start")

                # ── Step 1: Start Appium + navigate to feed ──────────────────
                svc.start_session()
                svc.navigate_to_feed()

                # ── Step 2: Scroll and collect post data (URLs + Engagement) ──
                posts_data = svc.scroll_and_collect_urls(scroll_count=scroll_count)
                logger.info("appium_posts_collected", count=len(posts_data))

                # ── Step 3: Filter + persist ────────────────────────────────
                saved = 0
                skipped = 0
                for post in posts_data:
                    try:
                        url = post["url"]
                        metadata = {
                            "reactions": post["reactions"],
                            "comments": post["comments"],
                            "reposts": post["reposts"]
                        }
                        
                        if passes_filters(
                            metadata["reactions"],
                            metadata["comments"],
                            metadata["reposts"],
                            filter_cfg,
                        ):
                            await persist_post_url(url, metadata)
                            saved += 1
                        else:
                            skipped += 1
                            logger.info(
                                "appium_post_filtered",
                                url=url[:60],
                                **metadata,
                                reason="thresholds_not_met"
                            )
                    except Exception as e:
                        logger.error("appium_url_processing_error", url=str(post.get("url", "unknown")), error=str(e))

                logger.info(
                    "appium_ingestion_cycle_done",
                    collected=len(posts_data),
                    saved=saved,
                    skipped=skipped,
                )

            except KeyboardInterrupt:
                logger.info("appium_worker_keyboard_interrupt")
                break
            except Exception as e:
                logger.error("appium_worker_critical_failure", error=str(e))
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)
                # Don't crash the loop — sleep and retry
            finally:
                try:
                    svc.end_session()
                except Exception:
                    pass

            logger.info("appium_worker_sleeping", seconds=sleep_interval)
            await asyncio.sleep(sleep_interval)


async def main():
    """Entrypoint for `python -m app.workers.appium_ingestion_worker`."""
    worker = AppiumIngestionWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
