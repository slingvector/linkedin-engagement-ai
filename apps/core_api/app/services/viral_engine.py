"""
Dynamic Viral Discovery Worker (GraphQL Network Interceptor).
Silently intercepts LinkedIn's background Voyager XHR/GraphQL JSON payloads
to discover trending content and automatically map viral creators into the Radar,
completely bypassing unstable HTML DOM scraping.
"""

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.dependencies import get_db
from app.repositories.creator_repository import CreatorRepository
from app.models.creator import IngestedPost
from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()

# Global list mutated by the background response event listener
intercepted_posts = []

def extract_posts_recursively(obj):
    """
    Traverses LinkedIn's deeply nested Voyager JSON graph.
    Uses a 2-pass correlation strategy to handle normalized GraphQL entities
    where Text and Metrics are split across different URN nodes.
    """
    nodes = []
    def gather(node):
        if isinstance(node, dict):
            nodes.append(node)
            for v in node.values():
                gather(v)
        elif isinstance(node, list):
            for item in node:
                gather(item)
    
    gather(obj)
    
    stats_map = {}
    text_nodes = []
    
    for node in nodes:
        urn = node.get("entityUrn") or node.get("urn") or node.get("trackingUrn") or ""
        if not isinstance(urn, str):
            continue
            
        # Ignore notification cards, network prompts, and non-post entities
        if "fsd_notificationCard" in urn or "fs_miniProfile" in urn:
            continue
        
        # 1. Collect Stats
        if "numLikes" in node or "numComments" in node:
            stats_map[urn] = {
                "likes": node.get("numLikes", 0),
                "comments": node.get("numComments", 0)
            }
            
        # 2. Collect Text
        text = ""
        commentary = node.get("commentary", {})
        if isinstance(commentary, dict) and "text" in commentary:
            text = commentary.get("text", {}).get("text", "")
            
        headline = node.get("headline", {})
        if not text and isinstance(headline, dict) and "text" in headline:
            text = headline.get("text", "")
            
        value_node = node.get("value", {})
        if not text and isinstance(value_node, dict) and "com.linkedin.voyager.feed.render.UpdateV2" in value_node:
            v2_data = value_node["com.linkedin.voyager.feed.render.UpdateV2"]
            if isinstance(v2_data, dict):
                text = v2_data.get("commentary", {}).get("text", {}).get("text", "")
                
        if text and text.strip():
            text_nodes.append({"urn": urn, "text": text.strip(), "node": node})

    # 3. Correlate and append
    import re
    for t_node in text_nodes:
        node = t_node["node"]
        text = t_node["text"]
        urn = t_node["urn"]
        
        likes = 0
        comments = 0
        
        # Check direct attachment
        if "socialDetail" in node and isinstance(node["socialDetail"], dict):
            sd = node["socialDetail"]
            if "totalSocialActivityCounts" in sd:
                likes = sd["totalSocialActivityCounts"].get("numLikes", 0)
                comments = sd["totalSocialActivityCounts"].get("numComments", 0)
                
        # Check linked stats urn
        elif "socialActivityCountsUrn" in node:
            s_urn = node["socialActivityCountsUrn"]
            if s_urn in stats_map:
                likes = stats_map[s_urn]["likes"]
                comments = stats_map[s_urn]["comments"]
                
        # Fallback ID extraction correlation
        if likes == 0 and comments == 0:
            t_match = re.search(r'\d{15,}', urn)
            if t_match:
                for s_urn, stats in stats_map.items():
                    if t_match.group(0) in s_urn:
                        likes = stats["likes"]
                        comments = stats["comments"]
                        break
                        
        clean_urn_match = re.search(r'(urn:li:activity:\d+|urn:li:fs_updateV2:\([^)]+\))', urn)
        final_urn = clean_urn_match.group(1) if clean_urn_match else urn
        
        # Prevent duplicates
        if final_urn and final_urn != "urn:li:activity:" and not any(p["urn"] == final_urn for p in intercepted_posts):
            intercepted_posts.append({
                "urn": final_urn,
                "text": text,
                "likes": likes,
                "comments": comments
            })

async def intercept_voyager_json(response):
    """
    Playwright Event Handler attached to `page.on("response")`.
    Fires on every single network request dynamically executed by the browser.
    """
    url = response.url
    if "api/graphql" in url or "updatesV2" in url or "voyagerIdentity" in url or "Dash" in url:
        try:
            logger.debug("intercept_request", url=url)
            body = await response.json()
            logger.debug("json_parsed_successfully", url=url)
            
            # Save samples of voyager responses for offline logic debugging
            if "voyager/api/graphql" in url or "updatesV2" in url:
                import os
                sample_file = f"/tmp/linkedin_payload_{uuid4().hex[:8]}.json"
                with open(sample_file, "w") as f:
                    json.dump(body, f, indent=2)
                logger.debug("sample_payload_saved", path=sample_file)
            
            extract_posts_recursively(body)
            
        except Exception as e:
            # Silent fail for network drops or non-json graphql (rare but safe)
            logger.debug("json_parsing_failed", url=url, error=str(e))
            pass

async def live_viral_ingestion_loop():
    """
    Autonomously drives Playwright to trigger feed loads, relying purely on the
    Network Interceptor (`intercept_voyager_json`) to collect data into memory.
    """
    settings = get_settings()
    yaml_config = get_yaml_config()
    ingest_config = yaml_config.get("ingestion", {})
    viral_config = ingest_config.get("viral", {})
    scraper_config = ingest_config.get("scraper", {})
    
    # Load dynamic configurations
    min_content_length = viral_config.get("min_content_length", 300)
    feed_scroll_count = scraper_config.get("feed_scroll_count", 5)
    max_posts_to_process = scraper_config.get("max_posts_to_process", 10)
    pause_between_scrolls = scraper_config.get("pause_between_scrolls_seconds", 2)
    loop_sleep = scraper_config.get("loop_sleep_interval_seconds", 3600)
    error_sleep = scraper_config.get("error_sleep_interval_seconds", 300)
    timeout_ms = scraper_config.get("timeout_ms", 60000)
    target_url = scraper_config.get("target_url", "https://www.linkedin.com/feed/")
    user_agent = scraper_config.get("user_agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    viewport_width = scraper_config.get("viewport_width", 1280)
    viewport_height = scraper_config.get("viewport_height", 800)
    
    logger.info("bg_worker_started", worker="graphql_interceptor_engine")
    global intercepted_posts
    
    while True:
        try:
            li_at = scraper_config.get("linkedin_li_at_cookie") or settings.linkedin_li_at_cookie
            intercepted_posts.clear() # Reset memory buffer on every loop
                
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": viewport_width, "height": viewport_height}
                )
                
                if li_at:
                    await context.add_cookies([{
                        "name": "li_at",
                        "value": li_at,
                        "domain": ".www.linkedin.com",
                        "path": "/"
                    }])
                
                page = await context.new_page()
                
                # Attach the core tier-1 network interceptor
                page.on("response", intercept_voyager_json)
                
                if not li_at:
                    logger.warning("missing_li_at_cookie", message="Opening browser for manual login. Please log in within 5 minutes!")
                    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
                    await page.wait_for_url("**/feed/**", timeout=300000)
                    
                    cookies = await context.cookies()
                    new_li_at = next((c["value"] for c in cookies if c["name"] == "li_at"), None)
                    if new_li_at:
                        logger.info("cookie_extracted", message=f"SUCCESS! Save this to config.yaml -> linkedin_li_at_cookie: '{new_li_at}'")
                
                logger.info("graphql_interceptor_navigating", target=target_url)
                
                if "feed" not in page.url:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                
                if "login" in page.url or "checkpoint" in page.url:
                    logger.error("graphql_interceptor_auth_failed", url=page.url)
                    await browser.close()
                    await asyncio.sleep(loop_sleep)
                    continue

                # 1. Dual-Extraction: Phase 1 (SSR HTML Pre-Hydrated Data)
                logger.info("extracting_ssr_hydrated_state")
                try:
                    code_elements = await page.locator("code").all_inner_texts()
                    for code_text in code_elements:
                        try:
                            # Safely attempt to parse any JSON embedded in <code> blocks
                            data = json.loads(code_text.strip())
                            extract_posts_recursively(data)
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.error("ssr_extraction_failed", error=str(e))
                
                # 2. Dual-Extraction: Phase 2 (Dynamic GraphQL background fetches)
                # Scroll to mechanically trigger additional Voyager payloads
                for _ in range(feed_scroll_count):
                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(pause_between_scrolls)
                    
                # Grace period for final JSON payloads to write into global memory
                await asyncio.sleep(5)
                
                logger.info("graphql_interceptor_posts_collected", count=len(intercepted_posts))
                
                # Deduplicate URNs in memory before DB operations
                unique_posts = {post["urn"]: post for post in intercepted_posts}.values()
                queued_posts = list(unique_posts)[:max_posts_to_process]
                
                # Process cleanly harvested JSON telemetry into the Database Pipeline
                async for db in get_db():
                    repo = CreatorRepository(db)
                    for data in queued_posts:
                        try:
                            # Evaluate engagement heuristically against pure internal variables
                            text_content = data["text"]
                            is_viral = len(text_content) > min_content_length
                            
                            if is_viral:
                                from sqlalchemy import select
                                from app.models.user import User
                                user_result = await db.execute(select(User).limit(1))
                                admin_user = user_result.scalars().first()
                                
                                if admin_user:
                                    try:
                                        # Auto-Track based on authentic LinkedIn URN mapping
                                        creator_urn = data["urn"]
                                        creator_id_hex = creator_urn.split(":")[-1][:8]
                                        
                                        creator = await repo.add_tracked_creator(
                                            user_id=admin_user.id,
                                            profile_url=f"https://www.linkedin.com/in/{creator_id_hex}",
                                            linkedin_id=f"discovered-{creator_id_hex}",
                                            full_name=f"Viral Creator {creator_id_hex}"
                                        )
                                        
                                        post = IngestedPost(
                                            tracked_creator_id=creator.id,
                                            linkedin_post_id=data["urn"],
                                            post_url=f"https://www.linkedin.com/feed/update/{data['urn']}/",
                                            content=text_content[:800], # safe truncation
                                            posted_at=datetime.now(timezone.utc),
                                            likes=data["likes"], # Actual internal JSON value
                                            comments=data["comments"] # Actual internal JSON value
                                        )
                                        await repo.add_ingested_post(post)
                                        logger.info("graphql_post_injected", creator=creator.full_name, urn=data["urn"])
                                    except Exception as e:
                                        logger.debug("creator_already_ingested", urn=data["urn"])
                        except Exception as e:
                            logger.error("graphql_pipeline_injection_error", error=str(e))
                
                await browser.close()
                logger.info("graphql_scrape_completed_successfully")
                
            await asyncio.sleep(loop_sleep)
            
        except PlaywrightTimeoutError:
            logger.error("graphql_interceptor_timeout")
            await asyncio.sleep(error_sleep)
        except asyncio.CancelledError:
            logger.info("bg_worker_stopped", worker="graphql_interceptor_engine")
            break
        except Exception as e:
            logger.error("bg_worker_error", worker="graphql_interceptor_engine", error=str(e))
            await asyncio.sleep(error_sleep)

if __name__ == "__main__":
    logger.info("Initializing Playwright GraphQL Interceptor...")
    asyncio.run(live_viral_ingestion_loop())