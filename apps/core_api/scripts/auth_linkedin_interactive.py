import asyncio
from playwright.async_api import async_playwright
import structlog

logger = structlog.get_logger()

async def interactive_login():
    print("🚀 Launching interactive browser...")
    print("👉 Please log into LinkedIn. The browser will automatically close once you are successfully logged in and the session cookie is secured.")
    
    async with async_playwright() as p:
        # Launch non-headless so you can see it and interact
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.goto("https://www.linkedin.com/login")
        
        # We wait until the URL changes from the login page, meaning success, or wait for the cookie to appear.
        li_at_value = None
        
        while not li_at_value:
            await asyncio.sleep(2)
            cookies = await context.cookies()
            for cookie in cookies:
                if cookie["name"] == "li_at":
                    li_at_value = cookie["value"]
                    break
                    
        print("\n✅ Success! Captured 'li_at' session cookie securely.")
        print(f"Your cookie value is: {li_at_value}")
        print("\nNow you can run: python scripts/create_test_user.py and paste this exact value!")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(interactive_login())
