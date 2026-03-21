import asyncio
import structlog
from typing import List, Dict, Any
from playwright.async_api import async_playwright

logger = structlog.get_logger()

async def scrape_creator_posts(profile_url: str, li_at_cookie: str) -> List[Dict[str, Any]]:
    """
    Tier 1 Network Interceptor: Real-world Playwright scraper for LinkedIn recent activity.
    Requires a valid li_at authentication cookie to bypass login walls.
    """
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Inject authentication cookie
        await context.add_cookies([
            {"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com", "path": "/"}
        ])
        
        page = await context.new_page()
        
        # Format URL to ensure we hit the activity shares feed
        clean_url = profile_url.split("?")[0].rstrip("/")
        if "recent-activity" not in clean_url:
            shares_url = f"{clean_url}/recent-activity/shares/"
        else:
            shares_url = clean_url
            
        logger.info("playwright_navigating", target_url=shares_url)
        
        try:
            await page.goto(shares_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for content or auth failure
            await page.wait_for_selector(".feed-shared-update-v2", timeout=15000)
            
            # Grab all loaded posts
            post_elements = await page.query_selector_all(".feed-shared-update-v2")
            logger.info("playwright_posts_found", count=len(post_elements))
            
            for index, el in enumerate(post_elements[:5]):  # Get top 5 recent posts
                try:
                    # Extract raw text components 
                    # Note: Full extraction requires precise selectors that frequently change
                    text_content = await el.inner_text()
                    urn_element = await el.get_attribute("data-urn")
                    
                    if text_content:
                        results.append({
                            "linkedin_post_id": urn_element or f"urn:li:scraped:{index}",
                            "raw_text": text_content,
                            "post_url": shares_url
                        })
                except Exception as e:
                    logger.warning("playwright_element_parse_error", error=str(e))
                    
        except Exception as e:
            # Could be timeout, auth wall, or invalid URL
            logger.error("playwright_scrape_failed", error=str(e), url=shares_url)
        finally:
            await browser.close()
            
    return results

if __name__ == "__main__":
    # Local CLI test mode
    import sys
    if len(sys.argv) < 3:
        print("Usage: python playwright_scraper.py <profile_url> <li_at_cookie>")
    else:
        posts = asyncio.run(scrape_creator_posts(sys.argv[1], sys.argv[2]))
        print(f"Scraped {len(posts)} posts. Sample Data:")
        for idx, p in enumerate(posts):
            print(f"--- Post {idx} ---\n{p['raw_text'][:200]}...\n")
