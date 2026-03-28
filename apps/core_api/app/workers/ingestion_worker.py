"""
Two-Tier Viral Discovery Worker.
================================

Tier 1 (Primary):   GraphQL/Voyager network interceptor. Captures pristine JSON.
                    Zero LLM cost. Robustly correlates text + metrics.

Tier 2 (Fallback):  LLM semantic parser. Fires ONLY when Tier 1 yields zero 
                    posts (e.g. anti-bot blocking, auth failure).

Uses a configuration flag `use_tiered_ingestion` in `config.yaml` to toggle
between this new architecture and the legacy scraper.
"""

import asyncio
import json
import re
import structlog
from datetime import datetime, timezone
from uuid import uuid4
from asyncio import Lock
from typing import Optional, Any

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

from app.dependencies import get_db
from app.repositories.creator_repository import CreatorRepository
from app.models.creator import IngestedPost, TrackedCreator
from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class RawPost(BaseModel):
    """Normalized post data produced by either Tier 1 or Tier 2."""
    post_urn: str
    author_urn: str = ""
    author_name: str = "Unknown"
    author_profile_id: str = ""
    text: str
    likes: int = 0
    comments: int = 0
    extracted_by: str = "interceptor"  # "interceptor" | "llm_parser" | "ssr"

class PostBuffer:
    """Thread-safe, deduplicated collector for intercepted posts."""
    def __init__(self):
        self._lock = Lock()
        self._posts: dict[str, RawPost] = {}

    async def add(self, post: RawPost) -> bool:
        async with self._lock:
            if post.post_urn in self._posts:
                return False
            self._posts[post.post_urn] = post
            return True

    async def drain(self) -> list[RawPost]:
        async with self._lock:
            posts = list(self._posts.values())
            self._posts.clear()
            return posts

    async def count(self) -> int:
        async with self._lock:
            return len(self._posts)

# ---------------------------------------------------------------------------
# Tier 1: Voyager logic
# ---------------------------------------------------------------------------

def extract_author_urn(node: dict) -> str:
    """Resolves actor URN from various Voyager schema paths."""
    for path in [
        node.get("actor", {}).get("urn"),
        node.get("actor", {}).get("entityUrn"),
        node.get("socialContent", {}).get("member", {}).get("entityUrn"),
        node.get("updateMetadata", {}).get("urn")
    ]:
        if path and isinstance(path, str) and ("miniProfile" in path or "member" in path):
            return path
    return ""

def parse_voyager_payload(payload: dict) -> list[RawPost]:
    """
    Core extraction logic. Traverses the graph, correlates stats,
    and enforces strict filtering rules.
    """
    nodes = []
    def gather(obj):
        if isinstance(obj, dict):
            nodes.append(obj)
            for v in obj.values():
                gather(v)
        elif isinstance(obj, list):
            for item in obj:
                gather(item)
    gather(payload)

    stats_map = {}
    profile_map = {}
    candidates = []

    for node in nodes:
        urn = node.get("entityUrn") or node.get("urn") or node.get("trackingUrn") or ""
        if not isinstance(urn, str): continue
        
        # --- Strict Filter (Phase 7 fix) ---
        urn_l = urn.lower()
        if any(x in urn_l for x in ["notificationcard", "miniprofile", "promoted", "suggested"]):
            if "miniprofile" in urn_l: profile_map[urn] = node
            continue

        # Stats
        if "numLikes" in node or "numComments" in node:
            stats_map[urn] = {"l": node.get("numLikes", 0), "c": node.get("numComments", 0)}

        # Text
        text = ""
        paths = [
            node.get("commentary", {}).get("text", {}).get("text"),
            node.get("value", {}).get("com.linkedin.voyager.feed.render.UpdateV2", {}).get("commentary", {}).get("text", {}).get("text"),
            node.get("headline", {}).get("text")
        ]
        for p in paths:
            if p and isinstance(p, str): 
                text = p
                break
        
        if text and text.strip() and urn:
            candidates.append({"urn": urn, "text": text.strip(), "node": node})

    results = []
    seen = set()
    for cand in candidates:
        urn, text, node = cand["urn"], cand["text"], cand["node"]
        
        match = re.search(r'(urn:li:activity:\d+|urn:li:fs_updateV2:\([^)]+\))', urn)
        if not match: continue
        post_urn = match.group(0)
        
        if post_urn in seen: continue
        seen.add(post_urn)

        likes, comments = 0, 0
        if urn in stats_map:
            likes, comments = stats_map[urn]["l"], stats_map[urn]["c"]
        else:
            id_match = re.search(r'\d{15,}', urn)
            if id_match:
                for s_urn, s in stats_map.items():
                    if id_match.group(0) in s_urn:
                        likes, comments = s["l"], s["c"]
                        break

        author_urn = extract_author_urn(node)
        author_name = "Unknown"
        profile_id = ""
        
        if author_urn:
            profile_id = author_urn.split(":")[-1][:8]
            if author_urn in profile_map:
                p_node = profile_map[author_urn]
                author_name = p_node.get("firstName", "") + " " + p_node.get("lastName", "")
                author_name = author_name.strip() or "Unknown"

        results.append(RawPost(
            post_urn=post_urn,
            author_urn=author_urn,
            author_name=author_name,
            author_profile_id=profile_id,
            text=text,
            likes=likes,
            comments=comments,
            extracted_by="interceptor"
        ))
    return results

async def on_response(response, buffer: PostBuffer):
    url = response.url
    if any(p in url for p in ["voyager/api", "updatesV2", "graphql"]):
        try:
            body = await response.json()
            for post in parse_voyager_payload(body):
                await buffer.add(post)
        except: pass

async def extract_ssr_posts(page, buffer: PostBuffer):
    try:
        blocks = await page.locator("code").all_inner_texts()
        for b in blocks:
            try:
                data = json.loads(b.strip())
                for post in parse_voyager_payload(data):
                    post.extracted_by = "ssr"
                    await buffer.add(post)
            except: continue
    except: pass

# ---------------------------------------------------------------------------
# Tier 2: LLM Fallback (Mocked / Integrated via AI Engine Webhook)
# ---------------------------------------------------------------------------

async def tier2_llm_extract(html_content: str, config: dict) -> list[RawPost]:
    """Semantic fallback extraction via LLM."""
    try:
        # Don't prune! LinkedIn stores data in <script> tags which are vital for Tier 2.
        # We send the raw HTML to the LLM (first 150k chars).
        text = html_content[:150000]
        
        with open("/tmp/final_raw_html.txt", "w") as f:
            f.write(text)
        
        settings = get_settings()
        ai_url = settings.ai_engine_url
        ai_key = settings.ai_engine_api_key
        
        async with httpx.AsyncClient(timeout=45) as client:
            # We use the generic 'classifier' endpoint in ai_engine for now
            # or a specific 'extract' one if implemented.
            resp = await client.post(
                f"{ai_url}/webhooks/extract/posts", # NOTE: Requires implementation in ai_engine
                json={"html_text": text, "model": config.get("llm_model")},
                headers={"X-AI-API-Key": ai_key}
            )
            if resp.status_code == 200:
                data = resp.json().get("posts", [])
                return [RawPost(**p, extracted_by="llm_parser") for p in data]
    except Exception as e:
        logger.error("tier2_fallback_failed", error=str(e))
    return []

# ---------------------------------------------------------------------------
# Business Logic
# ---------------------------------------------------------------------------

def is_viral(post: RawPost, config: dict) -> bool:
    likes_t = config.get("min_likes_threshold", 500)
    comments_t = config.get("min_comments_threshold", 50)
    # OR logic: Viral if it clears EITHER threshold
    return post.likes >= likes_t or post.comments >= comments_t

async def persist_posts(posts: list[RawPost]):
    async for db in get_db():
        repo = CreatorRepository(db)
        from sqlalchemy import select
        from app.models.user import User
        u_res = await db.execute(select(User).limit(1))
        admin = u_res.scalars().first()
        if not admin: return

        for p in posts:
            try:
                creator = await repo.add_tracked_creator(
                    user_id=admin.id,
                    profile_url=f"https://www.linkedin.com/in/{p.author_profile_id or 'unknown'}",
                    linkedin_id=f"discovered-{p.author_profile_id or uuid4().hex[:6]}",
                    full_name=p.author_name
                )
                ingested = IngestedPost(
                    tracked_creator_id=creator.id,
                    linkedin_post_id=p.post_urn,
                    post_url=f"https://www.linkedin.com/feed/update/{p.post_urn}/",
                    content=p.text[:800],
                    posted_at=datetime.now(timezone.utc),
                    likes=p.likes,
                    comments=p.comments,
                    ingestion_source="scheduled"
                )
                await repo.add_ingested_post(ingested)
                logger.info("post_ingested", urn=p.post_urn, by=p.extracted_by)
            except: pass

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

async def live_viral_ingestion_loop():
    settings = get_settings()
    yaml_config = get_yaml_config()
    ingest_cfg = yaml_config.get("ingestion", {})
    scraper_cfg = ingest_cfg.get("scraper", {})
    
    use_tiered = ingest_cfg.get("use_tiered_ingestion", False)
    logger.info("ingestion_worker_standby", tiered_mode=use_tiered)

    while True:
        try:
            li_at = scraper_cfg.get("linkedin_li_at_cookie") or settings.linkedin_li_at_cookie
            buffer = PostBuffer()

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=scraper_cfg.get("user_agent"))
                if li_at:
                    await context.add_cookies([{"name": "li_at", "value": li_at, "domain": ".www.linkedin.com", "path": "/"}])
                
                page = await context.new_page()
                page.on("response", lambda r: asyncio.ensure_future(on_response(r, buffer)))
                
                await page.goto(scraper_cfg.get("target_url"), wait_until="domcontentloaded", timeout=60000)
                await extract_ssr_posts(page, buffer)

                # Scroll loop
                for _ in range(scraper_cfg.get("feed_scroll_count", 5)):
                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(2)
                
                await asyncio.sleep(5) # Grace
                count = await buffer.count()
                
                if count == 0 and use_tiered:
                    logger.warning("tier1_found_nothing_firing_tier2")
                    html = await page.content()
                    t2_posts = await tier2_llm_extract(html, ingest_cfg.get("llm_parser", {}))
                    for p_raw in t2_posts: await buffer.add(p_raw)

                await browser.close()

            # Process & Persist
            all_captured = await buffer.drain()
            viral = [p for p in all_captured if is_viral(p, ingest_cfg.get("viral", {}))]
            logger.info("ingestion_summary", captured=len(all_captured), viral=len(viral))
            
            if viral:
                await persist_posts(viral)

            await asyncio.sleep(scraper_cfg.get("loop_sleep_interval_seconds", 3600))
        except Exception as e:
            logger.error("worker_loop_error", error=str(e))
            await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(live_viral_ingestion_loop())
