"""
Viral Discovery Worker — Two-Tier Ingestion Architecture
=========================================================

Tier 1 (Primary):   Playwright GraphQL/Voyager network interceptor.
                    Captures pristine JSON mid-flight. Zero LLM cost.
                    Extracts author URN, post URN, text, likes, comments.

Tier 2 (Fallback):  AI semantic parser. Fires ONLY when Tier 1 yields
                    zero posts (e.g. encrypted payload, auth failure).
                    Uses OpenAI structured outputs against CreatorPost schema.

Pipeline:
  Playwright  ──►  Response listener  ──►  Thread-safe buffer
                         │                        │
                   (if 0 posts)           Pydantic normaliser
                         │                        │
                  HTML sanitiser          Engagement filter
                         │                        │
                   LLM extractor          Author resolver
                         │                        │
                   CreatorPost ───────────────────►  DB upsert
"""

import asyncio
import json
import re
from asyncio import Lock
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import structlog
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from app.dependencies import get_db_session          # direct AsyncSession factory, NOT get_db()
from app.repositories.creator_repository import CreatorRepository
from app.models.creator import IngestedPost
from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Pydantic schemas — the single source of truth for extracted data
# ---------------------------------------------------------------------------

class RawPost(BaseModel):
    """Intermediate model produced by Tier 1 interceptor or Tier 2 LLM parser."""
    post_urn: str
    author_urn: str                        # e.g. urn:li:fs_miniProfile:ACoAAB...
    author_name: str = "Unknown"
    author_profile_id: str = ""           # the public vanity slug or numeric ID
    text: str
    likes: int = 0
    comments: int = 0
    extracted_by: str = "interceptor"     # "interceptor" | "llm_parser"


class LLMCreatorPost(BaseModel):
    """Structured output schema sent to OpenAI when Tier 2 fires."""
    post_urn: str = Field(description="LinkedIn activity URN, e.g. urn:li:activity:1234")
    author_name: str = Field(description="Full name of the post author")
    author_profile_url: str = Field(description="LinkedIn profile URL of the author")
    text: str = Field(description="Full text content of the post")
    likes: int = Field(default=0, description="Number of likes")
    comments: int = Field(default=0, description="Number of comments")


# ---------------------------------------------------------------------------
# Engagement thresholds — the real virality signal
# ---------------------------------------------------------------------------

VIRAL_MIN_LIKES    = 500
VIRAL_MIN_COMMENTS = 50
# A post is viral if it clears EITHER threshold (OR logic)
# Adjust in yaml_config under ingestion.viral.min_likes / min_comments


# ---------------------------------------------------------------------------
# Thread-safe post buffer
# ---------------------------------------------------------------------------

class PostBuffer:
    """
    Async-safe deduplicated buffer for posts captured across concurrent
    Playwright response events. Uses asyncio.Lock (not threading.Lock)
    because all Playwright callbacks run in the same event loop.
    """
    def __init__(self):
        self._lock = Lock()
        self._posts: dict[str, RawPost] = {}  # keyed by post_urn

    async def add(self, post: RawPost) -> bool:
        """Returns True if the post was new, False if duplicate."""
        async with self._lock:
            if post.post_urn in self._posts:
                return False
            self._posts[post.post_urn] = post
            return True

    async def drain(self) -> list[RawPost]:
        """Return all posts and clear the buffer atomically."""
        async with self._lock:
            posts = list(self._posts.values())
            self._posts.clear()
            return posts

    async def count(self) -> int:
        async with self._lock:
            return len(self._posts)


# ---------------------------------------------------------------------------
# Tier 1: Voyager JSON extraction
# ---------------------------------------------------------------------------

def extract_author_urn(node: dict) -> str:
    """
    Resolves the author/actor URN from a Voyager post node.

    LinkedIn's Voyager JSON represents the post author under several
    different key paths depending on the endpoint version. We check
    all known paths in priority order.
    """
    # Path A: updateV2 actor (most common in /feed/updatesV2 responses)
    actor = node.get("actor", {})
    if isinstance(actor, dict):
        urn = actor.get("urn", "") or actor.get("entityUrn", "")
        if urn and "fs_miniProfile" in urn:
            return urn

    # Path B: socialContent.member
    social = node.get("socialContent", {})
    if isinstance(social, dict):
        member = social.get("member", {})
        if isinstance(member, dict):
            urn = member.get("entityUrn", "")
            if urn:
                return urn

    # Path C: updateMetadata.urn (older Voyager schema)
    metadata = node.get("updateMetadata", {})
    if isinstance(metadata, dict):
        urn = metadata.get("urn", "")
        if urn and "miniProfile" in urn:
            return urn

    # Path D: headerImage.attributes[0].miniProfile.entityUrn
    header = node.get("headerImage", {})
    if isinstance(header, dict):
        for attr in header.get("attributes", []):
            mini = attr.get("miniProfile", {})
            if isinstance(mini, dict):
                urn = mini.get("entityUrn", "")
                if urn:
                    return urn

    return ""


def extract_author_name(node: dict) -> str:
    """Extract display name from actor/miniProfile nodes."""
    actor = node.get("actor", {})
    if isinstance(actor, dict):
        name = actor.get("name", {})
        if isinstance(name, dict):
            return name.get("text", "")
        if isinstance(name, str):
            return name

    # miniProfile firstName + lastName
    first = node.get("firstName", {})
    last  = node.get("lastName", {})
    if first or last:
        f = first.get("text", "") if isinstance(first, dict) else str(first)
        l = last.get("text", "")  if isinstance(last, dict)  else str(last)
        full = f"{f} {l}".strip()
        if full:
            return full

    return ""


def extract_public_identifier(author_urn: str, node: dict) -> str:
    """
    Extract the vanity slug or numeric ID usable in a LinkedIn profile URL.

    Prefers publicIdentifier (vanity slug) over numeric ID so the URL
    resolves to the actual profile page.
    """
    pub = node.get("publicIdentifier", "") or node.get("vanityName", "")
    if pub:
        return pub

    # Fall back to numeric suffix of the miniProfile URN
    match = re.search(r'miniProfile:([A-Za-z0-9_-]+)', author_urn)
    if match:
        return match.group(1)

    return ""


def parse_voyager_payload(payload: dict) -> list[RawPost]:
    """
    Two-pass correlation over a Voyager JSON graph.

    Pass 1: Collect all nodes into typed buckets.
      - post_nodes:   nodes containing commentary/text + post URN
      - stats_nodes:  nodes containing numLikes/numComments
      - profile_nodes: miniProfile nodes (name + publicIdentifier)

    Pass 2: Correlate posts → stats → profile by URN linkage.
    """
    all_nodes: list[dict] = []

    def gather(obj):
        if isinstance(obj, dict):
            all_nodes.append(obj)
            for v in obj.values():
                gather(v)
        elif isinstance(obj, list):
            for item in obj:
                gather(item)

    gather(payload)

    # --- Pass 1: bucket nodes ---
    stats_by_urn:   dict[str, dict] = {}   # urn → {likes, comments}
    profile_by_urn: dict[str, dict] = {}   # miniProfile urn → node

    post_candidates: list[dict] = []

    for node in all_nodes:
        if not isinstance(node, dict):
            continue

        urn = (
            node.get("entityUrn") or
            node.get("urn") or
            node.get("trackingUrn") or ""
        )
        if not isinstance(urn, str):
            urn = ""

        # Profile nodes — collect these even though we skip them as post sources
        if "fs_miniProfile" in urn or "miniProfile" in urn:
            profile_by_urn[urn] = node
            continue

        # Stats nodes
        if "numLikes" in node or "numComments" in node:
            stats_by_urn[urn] = {
                "likes":    node.get("numLikes", 0),
                "comments": node.get("numComments", 0),
            }

        # Inline socialDetail stats (takes priority over separate stats node)
        social_detail = node.get("socialDetail", {})
        if isinstance(social_detail, dict):
            counts = social_detail.get("totalSocialActivityCounts", {})
            if isinstance(counts, dict) and ("numLikes" in counts or "numComments" in counts):
                stats_by_urn[urn] = {
                    "likes":    counts.get("numLikes", 0),
                    "comments": counts.get("numComments", 0),
                }

        # Post text extraction — multiple Voyager schema versions
        text = ""

        # Schema v1: commentary.text.text
        commentary = node.get("commentary", {})
        if isinstance(commentary, dict):
            inner = commentary.get("text", {})
            text = inner.get("text", "") if isinstance(inner, dict) else str(inner)

        # Schema v2: value["com.linkedin.voyager.feed.render.UpdateV2"].commentary
        if not text:
            value = node.get("value", {})
            if isinstance(value, dict):
                v2 = value.get("com.linkedin.voyager.feed.render.UpdateV2", {})
                if isinstance(v2, dict):
                    c = v2.get("commentary", {})
                    if isinstance(c, dict):
                        inner = c.get("text", {})
                        text = inner.get("text", "") if isinstance(inner, dict) else ""

        # Schema v3: headline.text (articles / shared posts)
        if not text:
            headline = node.get("headline", {})
            if isinstance(headline, dict):
                text = headline.get("text", "")

        if text and text.strip() and urn:
            node["_extracted_text"] = text.strip()
            node["_urn"] = urn
            post_candidates.append(node)

    # --- Pass 2: correlate ---
    results: list[RawPost] = []
    seen_urns: set[str] = set()

    for node in post_candidates:
        urn  = node["_urn"]
        text = node["_extracted_text"]

        # Normalise URN to activity format
        clean_match = re.search(
            r'(urn:li:activity:\d+|urn:li:fs_updateV2:\([^)]+\))',
            urn
        )
        post_urn = clean_match.group(1) if clean_match else urn

        if not post_urn or post_urn in seen_urns:
            continue
        seen_urns.add(post_urn)

        # --- Resolve stats ---
        likes    = 0
        comments = 0

        if urn in stats_by_urn:
            likes    = stats_by_urn[urn]["likes"]
            comments = stats_by_urn[urn]["comments"]
        elif "socialActivityCountsUrn" in node:
            s_urn = node["socialActivityCountsUrn"]
            if s_urn in stats_by_urn:
                likes    = stats_by_urn[s_urn]["likes"]
                comments = stats_by_urn[s_urn]["comments"]
        else:
            # Numeric ID correlation: extract the 15+ digit activity ID
            # and scan stats_by_urn for a matching key
            id_match = re.search(r'\d{15,}', urn)
            if id_match:
                activity_id = id_match.group(0)
                for s_urn, stats in stats_by_urn.items():
                    if activity_id in s_urn:
                        likes    = stats["likes"]
                        comments = stats["comments"]
                        break

        # --- Resolve author ---
        author_urn  = extract_author_urn(node)
        author_name = extract_author_name(node)
        public_id   = ""

        # Look up full miniProfile node for richer name/slug data
        if author_urn and author_urn in profile_by_urn:
            profile_node = profile_by_urn[author_urn]
            if not author_name:
                author_name = extract_author_name(profile_node)
            public_id = extract_public_identifier(author_urn, profile_node)
        elif author_urn:
            public_id = extract_public_identifier(author_urn, {})

        results.append(RawPost(
            post_urn=post_urn,
            author_urn=author_urn,
            author_name=author_name or "Unknown",
            author_profile_id=public_id,
            text=text,
            likes=likes,
            comments=comments,
            extracted_by="interceptor",
        ))

    return results


# ---------------------------------------------------------------------------
# Tier 1: Playwright response event handler
# ---------------------------------------------------------------------------

async def on_response(response, buffer: PostBuffer):
    """
    Fires on every network response from the Playwright page.
    Only processes LinkedIn Voyager API / GraphQL endpoints.
    Writes RawPost entries into the shared thread-safe buffer.
    """
    url = response.url
    voyager_patterns = (
        "voyager/api/graphql",
        "voyager/api/feed",
        "updatesV2",
        "api/graphql",
    )
    if not any(p in url for p in voyager_patterns):
        return

    try:
        body = await response.json()
    except Exception:
        # Non-JSON response (binary, empty, etc.) — skip silently
        return

    posts = parse_voyager_payload(body)
    new_count = 0
    for post in posts:
        added = await buffer.add(post)
        if added:
            new_count += 1

    if new_count:
        logger.debug("tier1_intercepted", url=url, new_posts=new_count)


# ---------------------------------------------------------------------------
# Tier 1: SSR hydrated state extraction (Phase 1 of Tier 1)
# ---------------------------------------------------------------------------

async def extract_ssr_posts(page, buffer: PostBuffer) -> int:
    """
    Scrapes pre-rendered JSON embedded in <code> tags in the page HTML.
    These are injected by LinkedIn's SSR layer before the SPA hydrates.
    Returns the number of new posts added.
    """
    added = 0
    try:
        code_blocks = await page.locator("code").all_inner_texts()
        for block in code_blocks:
            try:
                data = json.loads(block.strip())
                posts = parse_voyager_payload(data)
                for post in posts:
                    if await buffer.add(post):
                        added += 1
            except (json.JSONDecodeError, Exception):
                continue
    except Exception as e:
        logger.warning("ssr_extraction_error", error=str(e))
    return added


# ---------------------------------------------------------------------------
# Tier 2: AI semantic parser (fallback only)
# ---------------------------------------------------------------------------

async def tier2_llm_extract(html_content: str, config: dict) -> list[RawPost]:
    """
    Fallback parser. Sanitises HTML → Markdown → OpenAI structured output.

    Only called when Tier 1 yields zero posts for the current page load.
    Uses function-calling / structured output to force JSON conforming
    to LLMCreatorPost schema — immune to UI layout changes.
    """
    try:
        # --- Step 1: HTML → clean Markdown ---
        from bs4 import BeautifulSoup
        import markdownify

        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        clean_text = markdownify.markdownify(str(soup), heading_style="ATX")
        # Truncate to ~12k tokens (≈ 48k chars) to stay within context window
        clean_text = clean_text[:48_000]

        logger.info("tier2_html_sanitised", markdown_chars=len(clean_text))

        # --- Step 2: LLM structured extraction ---
        import openai
        client = openai.AsyncOpenAI()  # reads OPENAI_API_KEY from env

        system_prompt = (
            "You are a data extraction engine. Extract LinkedIn post data from "
            "the provided page text. Return ONLY a JSON array of objects with "
            "these fields: post_urn, author_name, author_profile_url, text, "
            "likes (integer), comments (integer). "
            "If a field is missing, use an empty string or 0. "
            "Do NOT include markdown fences or any explanation."
        )

        response = await client.chat.completions.create(
            model=config.get("llm_model", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": clean_text},
            ],
            max_tokens=4096,
        )

        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        # The model may return {"posts": [...]} or just [...]
        items = data if isinstance(data, list) else data.get("posts", [])

        results: list[RawPost] = []
        for item in items:
            try:
                parsed = LLMCreatorPost(**item)
                # Derive author_profile_id from profile URL
                slug_match = re.search(r'linkedin\.com/in/([^/?#]+)', parsed.author_profile_url)
                profile_id = slug_match.group(1) if slug_match else ""

                results.append(RawPost(
                    post_urn=parsed.post_urn or f"urn:li:activity:{uuid4().int >> 64}",
                    author_urn="",                 # not resolvable from HTML
                    author_name=parsed.author_name,
                    author_profile_id=profile_id,
                    text=parsed.text,
                    likes=parsed.likes,
                    comments=parsed.comments,
                    extracted_by="llm_parser",
                ))
            except Exception as e:
                logger.warning("tier2_item_parse_error", error=str(e), item=item)

        logger.info("tier2_llm_extracted", post_count=len(results))
        return results

    except Exception as e:
        logger.error("tier2_llm_error", error=str(e))
        return []


# ---------------------------------------------------------------------------
# Engagement filter — the real virality gate
# ---------------------------------------------------------------------------

def is_viral(post: RawPost, min_likes: int, min_comments: int) -> bool:
    """
    A post is viral if it clears EITHER the likes OR comments threshold.
    Completely replaces the broken character-count heuristic.
    """
    return post.likes >= min_likes or post.comments >= min_comments


# ---------------------------------------------------------------------------
# Author profile resolver
# ---------------------------------------------------------------------------

def resolve_profile_url(post: RawPost) -> str:
    """
    Build the best available LinkedIn profile URL.

    Priority:
      1. Vanity slug (publicIdentifier)  →  /in/john-doe
      2. miniProfile URN suffix          →  /in/ACoAAB...
      3. Placeholder for unknown authors
    """
    if post.author_profile_id:
        return f"https://www.linkedin.com/in/{post.author_profile_id}"
    if post.author_urn:
        urn_id = post.author_urn.split(":")[-1]
        return f"https://www.linkedin.com/in/{urn_id}"
    return ""


# ---------------------------------------------------------------------------
# DB persistence — correct session management for background workers
# ---------------------------------------------------------------------------

async def persist_posts(posts: list[RawPost], settings):
    """
    Uses a direct AsyncSession (not the FastAPI get_db() dependency) so
    the session lifecycle is explicitly managed by this background worker.
    """
    from app.db import AsyncSessionLocal  # direct session factory
    from sqlalchemy import select
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        async with db.begin():
            repo = CreatorRepository(db)

            # Fetch the admin user once per batch
            result = await db.execute(select(User).limit(1))
            admin_user = result.scalars().first()
            if not admin_user:
                logger.error("persist_no_admin_user")
                return

            for post in posts:
                try:
                    profile_url = resolve_profile_url(post)
                    if not profile_url:
                        logger.warning("persist_skip_no_profile", urn=post.post_urn)
                        continue

                    # Upsert creator — add_tracked_creator should be idempotent
                    # (insert-or-ignore on linkedin_id unique constraint)
                    linkedin_id = (
                        post.author_profile_id or
                        post.author_urn.split(":")[-1] or
                        f"discovered-{uuid4().hex[:8]}"
                    )

                    creator = await repo.add_tracked_creator(
                        user_id=admin_user.id,
                        profile_url=profile_url,
                        linkedin_id=linkedin_id,
                        full_name=post.author_name,
                    )

                    ingested = IngestedPost(
                        tracked_creator_id=creator.id,
                        linkedin_post_id=post.post_urn,
                        post_url=f"https://www.linkedin.com/feed/update/{post.post_urn}/",
                        content=post.text[:800],
                        posted_at=datetime.now(timezone.utc),
                        likes=post.likes,
                        comments=post.comments,
                    )
                    await repo.add_ingested_post(ingested)

                    logger.info(
                        "post_persisted",
                        author=post.author_name,
                        urn=post.post_urn,
                        likes=post.likes,
                        comments=post.comments,
                        via=post.extracted_by,
                    )

                except Exception as e:
                    logger.error("persist_post_error", urn=post.post_urn, error=str(e))


# ---------------------------------------------------------------------------
# Main worker loop
# ---------------------------------------------------------------------------

async def live_viral_ingestion_loop():
    """
    Two-tier ingestion loop:

      1. Launch Playwright in headless mode (always).
      2. Attach response interceptor to a thread-safe PostBuffer.
      3. Navigate to LinkedIn feed and scroll to trigger Voyager calls.
      4. Drain buffer → apply engagement filter → persist viral posts.
      5. If buffer is empty after scrolling → fire Tier 2 LLM fallback.
      6. Sleep and repeat.
    """
    settings    = get_settings()
    yaml_config = get_yaml_config()
    ingest_cfg  = yaml_config.get("ingestion", {})
    viral_cfg   = ingest_cfg.get("viral", {})
    scraper_cfg = ingest_cfg.get("scraper", {})
    llm_cfg     = ingest_cfg.get("llm_parser", {})

    # --- Load config with sane defaults ---
    min_likes          = viral_cfg.get("min_likes",                  VIRAL_MIN_LIKES)
    min_comments       = viral_cfg.get("min_comments",               VIRAL_MIN_COMMENTS)
    feed_scroll_count  = scraper_cfg.get("feed_scroll_count",        8)
    max_posts          = scraper_cfg.get("max_posts_to_process",     50)
    pause_between      = scraper_cfg.get("pause_between_scrolls_seconds", 2)
    loop_sleep         = scraper_cfg.get("loop_sleep_interval_seconds",   3600)
    error_sleep        = scraper_cfg.get("error_sleep_interval_seconds",  300)
    timeout_ms         = scraper_cfg.get("timeout_ms",               60_000)
    target_url         = scraper_cfg.get("target_url",               "https://www.linkedin.com/feed/")
    user_agent         = scraper_cfg.get(
        "user_agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36",
    )
    viewport_w = scraper_cfg.get("viewport_width",  1280)
    viewport_h = scraper_cfg.get("viewport_height",  800)

    li_at = scraper_cfg.get("linkedin_li_at_cookie") or settings.linkedin_li_at_cookie

    logger.info("worker_started", worker="two_tier_viral_discovery")

    while True:
        buffer = PostBuffer()  # fresh buffer every iteration

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,   # always headless in production
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": viewport_w, "height": viewport_h},
                    # Mask automation signals
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
                    },
                )

                if li_at:
                    await context.add_cookies([{
                        "name":   "li_at",
                        "value":  li_at,
                        "domain": ".www.linkedin.com",
                        "path":   "/",
                    }])
                else:
                    logger.warning(
                        "missing_li_at_cookie",
                        hint="Set linkedin_li_at_cookie in config.yaml or env",
                    )

                page = await context.new_page()

                # --- Attach Tier 1 interceptor ---
                page.on("response", lambda r: asyncio.ensure_future(on_response(r, buffer)))

                logger.info("navigating_to_feed", url=target_url)
                await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)

                # Auth guard
                if "login" in page.url or "checkpoint" in page.url:
                    logger.error("auth_failed", current_url=page.url)
                    await browser.close()
                    await asyncio.sleep(error_sleep)
                    continue

                # --- Tier 1, Phase 1: SSR extraction ---
                ssr_count = await extract_ssr_posts(page, buffer)
                logger.info("ssr_phase_complete", posts_found=ssr_count)

                # --- Tier 1, Phase 2: scroll to trigger dynamic Voyager calls ---
                for scroll_i in range(feed_scroll_count):
                    await page.mouse.wheel(0, 2500)
                    await asyncio.sleep(pause_between)
                    buffered = await buffer.count()
                    logger.debug("scroll_progress", scroll=scroll_i + 1, buffered=buffered)

                # Grace period for in-flight JSON responses to arrive
                await asyncio.sleep(5)

                tier1_count = await buffer.count()
                logger.info("tier1_complete", posts_buffered=tier1_count)

                # --- Tier 2 fallback: fires ONLY if Tier 1 found nothing ---
                if tier1_count == 0:
                    logger.warning("tier1_empty_activating_tier2_fallback")
                    html_content = await page.content()
                    tier2_posts  = await tier2_llm_extract(html_content, llm_cfg)
                    for post in tier2_posts:
                        await buffer.add(post)
                    logger.info("tier2_complete", posts_extracted=len(tier2_posts))

                await browser.close()

            # --- Drain buffer and apply virality filter ---
            all_posts = await buffer.drain()
            all_posts = all_posts[:max_posts]

            viral_posts = [p for p in all_posts if is_viral(p, min_likes, min_comments)]

            logger.info(
                "filter_complete",
                total=len(all_posts),
                viral=len(viral_posts),
                min_likes=min_likes,
                min_comments=min_comments,
            )

            # --- Persist viral posts ---
            if viral_posts:
                await persist_posts(viral_posts, settings)

            logger.info("iteration_complete", sleeping_seconds=loop_sleep)
            await asyncio.sleep(loop_sleep)

        except PlaywrightTimeoutError:
            logger.error("playwright_timeout", sleeping_seconds=error_sleep)
            await asyncio.sleep(error_sleep)

        except asyncio.CancelledError:
            logger.info("worker_stopped", worker="two_tier_viral_discovery")
            break

        except Exception as e:
            logger.error("worker_error", error=str(e), sleeping_seconds=error_sleep)
            await asyncio.sleep(error_sleep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(live_viral_ingestion_loop())
