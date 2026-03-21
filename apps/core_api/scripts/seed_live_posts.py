import asyncio
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User
from app.models.creator import TrackedCreator, IngestedPost
from app.workers.playwright_scraper import scrape_creator_posts

async def seed():
    settings=get_settings()
    engine=create_async_engine(settings.database_url)
    async_session=sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as s:
        user = (await s.execute(select(User).limit(1))).scalar_one()
        
        tc = TrackedCreator(
            user_id=user.id,
            linkedin_id="williamhgates",
            profile_url="https://www.linkedin.com/in/williamhgates",
            full_name="Bill Gates",
            headline="Chair, Gates Foundation",
            is_active=1
        )
        s.add(tc)
        await s.commit()
        await s.refresh(tc)
        
        cookie = "AQEDAWX3YegCVWPuAAABnRHoZnMAAAGdNfTqc04Ac5uOOE2hUWQAwgzLZZMd74nd3UqcOwsbPZVxt23Q-iYFgF8ajjdv4pP0J6TLtC_-mpfQfQK7Zg8VCKXo0WIu-yqVwF5C2mOeBg0JcLWCCpQxF5eo"
        print("Scraping live posts...")
        posts = await scrape_creator_posts("https://www.linkedin.com/in/williamhgates", cookie)
        
        for p in posts:
            ip = IngestedPost(
                tracked_creator_id=tc.id,
                linkedin_post_id=p.get("linkedin_post_id", f"urn:li:{uuid4().hex}"),
                post_url=p["post_url"],
                content=p["raw_text"],
                posted_at=datetime.utcnow(),
                likes=100,
                comments=20,
            )
            s.add(ip)
        await s.commit()
        print(f"Seeded {len(posts)} LIVE posts for E2E Test!")

if __name__ == "__main__":
    asyncio.run(seed())
