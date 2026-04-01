"""
Engagement Sync Worker — V2 Data Flywheel, Sprint 3 tail
=========================================================
Runs every 6 hours. For each user with stored LinkedIn OAuth tokens:

  1. Finds their recently published posts (< 7 days old, has linkedin_post_urn)
  2. Calls LinkedIn's shareStatistics API to pull live likes/comments/impressions
  3. Updates `likes`, `comments_count`, `impressions` + computes `actual_engagement_rate`
  4. If the post has a virality_score, triggers a recalibration via ViralityService
     (re-scores with updated top-performers calibration data)

actual_engagement_rate formula (stored as int * 1000 for DB indexing):
    (likes + comments_count * 3 + shares * 5) / impressions * 1000

LinkedIn API used:
    GET https://api.linkedin.com/v2/shares/{shareUrn}/statistics
    Authorization: Bearer {access_token}

If access_token is missing or expired, that user is skipped gracefully.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import _async_session
from app.models.post import Post
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.services.virality_service import ViralityService
from app.utils.security import decrypt_token

logger = structlog.get_logger()

# ── Constants ─────────────────────────────────────────────────────────────────

SYNC_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours
RECENCY_DAYS = 7                       # Only sync posts < 7 days old
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
HTTP_TIMEOUT = 15.0

# How much actual_engagement_rate must shift (absolute) to trigger a re-score.
# Stored as int * 1000, so 50 = 0.05 = 5% shift.
RESCORE_THRESHOLD = 50


# ── LinkedIn Metrics Fetcher ──────────────────────────────────────────────────

async def _fetch_post_stats(
    share_urn: str,
    access_token: str,
) -> dict | None:
    """
    Call LinkedIn's share statistics endpoint.

    Returns: {likes, comments, impressions, shares} or None on error.

    LinkedIn endpoint:
        GET /v2/shares/{id}/statistics
    Note: `share_urn` is the full URN like `urn:li:share:123456789`.
    We strip the ID portion for the URL path.
    """
    # Extract numeric ID from URN (e.g. "urn:li:share:123" → "123")
    share_id = share_urn.split(":")[-1]

    # Try the newer Posts API first (v202304+), fall back to legacy shares
    urls_to_try = [
        f"{LINKEDIN_API_BASE}/socialActions/{share_urn}",
        f"{LINKEDIN_API_BASE}/shares/{share_id}/statistics",
    ]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for url in urls_to_try:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # socialActions endpoint shape
                    if "likesSummary" in data:
                        return {
                            "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                            "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                            "shares": 0,
                            "impressions": 0,  # socialActions doesn't return impressions
                        }
                    # shares statistics endpoint shape
                    if "shareStatistics" in data:
                        stats = data["shareStatistics"]
                        return {
                            "likes": stats.get("likeCount", 0),
                            "comments": stats.get("commentCount", 0),
                            "shares": stats.get("shareCount", 0),
                            "impressions": stats.get("impressionCount", 0),
                        }
                elif resp.status_code in (401, 403):
                    logger.warning(
                        "linkedin_token_expired",
                        share_urn=share_urn,
                        status=resp.status_code,
                    )
                    return None
                # 404 / other → try next URL
            except httpx.RequestError as e:
                logger.warning("linkedin_stats_request_error", url=url, error=str(e))
                continue

    return None


# ── Engagement Rate Calculator ────────────────────────────────────────────────

def _compute_engagement_rate(likes: int, comments: int, shares: int, impressions: int) -> int:
    """
    Calculate engagement rate stored as int * 1000 (avoids float columns).
    Formula: (likes + comments*3 + shares*5) / impressions * 1000
    Returns 0 if impressions == 0.
    """
    if impressions <= 0:
        return 0
    rate = (likes + comments * 3 + shares * 5) / impressions
    return int(rate * 1000)


# ── Per-user Sync ─────────────────────────────────────────────────────────────

async def _sync_user_posts(user: User) -> None:
    """Sync all recent published posts for a single user."""

    # ── 1. Decrypt access token ───────────────────────────────────────────────
    if not user.access_token_encrypted:
        logger.debug("engagement_sync_skip_no_token", user_id=str(user.id))
        return

    try:
        access_token = decrypt_token(user.access_token_encrypted)
    except Exception as e:
        logger.warning("engagement_sync_token_decrypt_failed", user_id=str(user.id), error=str(e))
        return

    # ── 2. Query posts to sync ────────────────────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)

    async with _async_session() as db:
        result = await db.execute(
            select(Post).where(
                Post.user_id == user.id,
                Post.status == "published",
                Post.published_at.isnot(None),
                Post.published_at >= cutoff.replace(tzinfo=None),
                Post.deleted_at.is_(None),
            )
        )
        posts: list[Post] = list(result.scalars().all())

    if not posts:
        logger.debug("engagement_sync_no_posts", user_id=str(user.id))
        return

    logger.info(
        "engagement_sync_starting",
        user_id=str(user.id),
        post_count=len(posts),
    )

    synced = 0
    rescored = 0

    for post in posts:
        # ── 3. Get the linkedin_post_urn from generation_metadata ─────────────
        # Stored when the post is published via write-flow:
        # generation_metadata["linkedin_post_urn"] = "urn:li:share:123..."
        gen_meta: dict = post.generation_metadata or {}
        share_urn = gen_meta.get("linkedin_post_urn")

        if not share_urn:
            # No URN yet → post was published via simulated publish, skip metrics
            logger.debug(
                "engagement_sync_no_urn",
                post_id=str(post.id),
            )
            continue

        # ── 4. Fetch live stats from LinkedIn ─────────────────────────────────
        stats = await _fetch_post_stats(share_urn, access_token)
        if stats is None:
            continue

        likes = int(stats.get("likes", 0))
        comments = int(stats.get("comments", 0))
        shares = int(stats.get("shares", 0))
        impressions = int(stats.get("impressions", 0))

        new_engagement_rate = _compute_engagement_rate(likes, comments, shares, impressions)
        old_engagement_rate = post.actual_engagement_rate or 0

        # ── 5. Persist updated metrics ────────────────────────────────────────
        async with _async_session() as db:
            # Re-fetch post within session to avoid detached instance issues
            result = await db.execute(select(Post).where(Post.id == post.id))
            live_post = result.scalar_one_or_none()
            if not live_post:
                continue

            live_post.likes = likes
            live_post.comments_count = comments
            live_post.impressions = impressions
            live_post.actual_engagement_rate = new_engagement_rate

            await db.commit()
            synced += 1

            logger.info(
                "engagement_synced",
                post_id=str(post.id),
                likes=likes,
                comments=comments,
                impressions=impressions,
                engagement_rate=new_engagement_rate,
            )

        # ── 6. Trigger virality recalibration if score shifted significantly ──
        should_rescore = (
            post.virality_score is not None
            and abs(new_engagement_rate - old_engagement_rate) >= RESCORE_THRESHOLD
        )

        if should_rescore:
            try:
                async with _async_session() as db:
                    repo = PostRepository(db)
                    virality_service = ViralityService(repo, db)
                    await virality_service.score_post(post.id, user.id)
                    rescored += 1
                    logger.info(
                        "engagement_triggered_rescore",
                        post_id=str(post.id),
                        delta=new_engagement_rate - old_engagement_rate,
                    )
            except Exception as e:
                logger.warning(
                    "engagement_rescore_failed",
                    post_id=str(post.id),
                    error=str(e),
                )

        # Small delay between individual API calls to be rate-limit friendly
        await asyncio.sleep(0.5)

    logger.info(
        "engagement_sync_complete",
        user_id=str(user.id),
        synced=synced,
        rescored=rescored,
    )


# ── Main Worker Loop ──────────────────────────────────────────────────────────

async def engagement_sync_loop() -> None:
    """
    Background worker — runs every 6 hours.
    Iterates all users with stored tokens, syncs recent post metrics.
    """
    settings = get_settings()

    logger.info(
        "worker_started",
        worker="engagement_sync_loop",
        interval_hours=SYNC_INTERVAL_SECONDS // 3600,
        env=settings.environment,
    )

    while True:
        try:
            # ── Fetch all users with OAuth tokens ────────────────────────────
            async with _async_session() as db:
                result = await db.execute(
                    select(User).where(User.access_token_encrypted.isnot(None))
                )
                users: list[User] = list(result.scalars().all())

            logger.info("engagement_sync_run_started", user_count=len(users))

            for user in users:
                try:
                    await _sync_user_posts(user)
                except asyncio.CancelledError:
                    raise  # Propagate cancellation
                except Exception as e:
                    logger.error(
                        "engagement_sync_user_error",
                        user_id=str(user.id),
                        error=str(e),
                        exc_info=True,
                    )
                # Brief pause between users to avoid hammering LinkedIn
                await asyncio.sleep(2)

            logger.info("engagement_sync_run_complete", user_count=len(users))

        except asyncio.CancelledError:
            logger.info("worker_cancelled", worker="engagement_sync_loop")
            break
        except Exception as e:
            logger.error(
                "worker_error",
                worker="engagement_sync_loop",
                error=str(e),
                exc_info=True,
            )

        # Sleep until next cycle (6 hours)
        logger.info(
            "engagement_sync_sleeping",
            next_run_in_hours=SYNC_INTERVAL_SECONDS // 3600,
        )
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
