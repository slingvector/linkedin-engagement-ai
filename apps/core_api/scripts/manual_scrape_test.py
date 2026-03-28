import asyncio
import json
import structlog
from playwright.async_api import async_playwright
from app.workers.ingestion_worker import PostBuffer, on_response, extract_ssr_posts, persist_posts, is_viral, tier2_llm_extract
from app.config import get_settings, get_yaml_config

# Setup logging
logger = structlog.get_logger()

async def final_verification():
    """
    The definitive E2E test.
    """
    settings = get_settings()
    yaml_config = get_yaml_config()
    ingest_cfg = yaml_config.get("ingestion", {})
    scraper_cfg = ingest_cfg.get("scraper", {})
    
    li_at = scraper_cfg.get("linkedin_li_at_cookie") or settings.linkedin_li_at_cookie
    
    print("\n[+] STARTING FINAL E2E VERIFICATION (TWO-TIER)...")
    buffer = PostBuffer()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=scraper_cfg.get("user_agent"))
        await context.add_cookies([{"name": "li_at", "value": li_at, "domain": ".www.linkedin.com", "path": "/"}])
        page = await context.new_page()
        
        # Tier 1 Interceptor
        page.on("response", lambda r: asyncio.ensure_future(on_response(r, buffer)))
        
        print(f"[+] Navigating to {scraper_cfg.get('target_url')}...")
        await page.goto(scraper_cfg.get('target_url'), wait_until="commit", timeout=60000)
        
        print("[+] Waiting 30s for feed container to appear (Hydration)...")
        await asyncio.sleep(30)

        # Check for feed container or specific updates to confirm load
        feed_exists = await page.locator(".feed-shared-update-v2").count()
        print(f"[+] Feed update elements found: {feed_exists}")
        
        if feed_exists == 0:
            print("[!] WARNING: No feed elements visible yet. Taking debug snapshot.")
            await page.screenshot(path="/tmp/unhydrated_feed.png")
        
        # Phase 1: SSR
        await extract_ssr_posts(page, buffer)
        
        # Phase 2: Scrolling (Aggressive)
        for i in range(8):
            await page.mouse.wheel(0, 4000)
            await asyncio.sleep(4)
            print(f"    Scroll {i+1}, buffer state: {await buffer.count()}")

        await asyncio.sleep(5)
        count = await buffer.count()
        print(f"\n[+] Tier 1 Final Count: {count}")

        # Tier 2 Fallback Trigger
        if count == 0:
            print("[!] Tier 1 empty. FORCING TIER 2 (AI SEMANTIC PARSE)...")
            html = await page.content()
            t2_posts = await tier2_llm_extract(html, ingest_cfg.get("llm_parser", {}))
            for p_raw in t2_posts:
                await buffer.add(p_raw)
            print(f"[+] Tier 2 Result: {len(t2_posts)} posts extracted via AI")

        await browser.close()

    # Final tally
    all_captured = await buffer.drain()
    
    # Filter using the new 10/1 thresholds from config.yaml
    viral = [p for p in all_captured if is_viral(p, ingest_cfg.get("viral", {}))]
    
    print(f"\n[FINAL SUMMARY]")
    print(f"Total Unique Captured: {len(all_captured)}")
    print(f"Viral (Thresholds: {ingest_cfg.get('viral', {})}): {len(viral)}")

    if viral:
        print("\n[+] Injecting into database...")
        await persist_posts(viral[:10])
        print("[+] SUCCESS: Verification Complete.")
        for p in viral[:3]:
            print(f"    - Found: {p.author_name} ({p.post_urn})")
    else:
        print("\n[!] FAILURE: Ingestion pipeline yielded 0 posts. Likely auth block or layout shift.")

if __name__ == "__main__":
    asyncio.run(final_verification())
