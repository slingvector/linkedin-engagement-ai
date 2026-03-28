import asyncio
from datetime import datetime, timezone
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.sql import text
from app.config import get_settings
from app.models.user import User
from app.models.creator import TrackedCreator, IngestedPost
from app.repositories.creator_repository import CreatorRepository

async def inject_posts():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    posts_data = [
        {
            "urn": "urn:li:activity:7442208721109229569",
            "url": "https://www.linkedin.com/posts/gaganbiyani_a-junior-employee-really-screwed-up-last-share-7442208721109229569-Zy5b",
            "text": "A junior employee really screwed up last week...",
            "creator_name": "Gagan Biyani",
            "likes": 4200,
            "comments": 250
        },
        {
            "urn": "urn:li:activity:7437760105388990464",
            "url": "https://www.linkedin.com/posts/komalmundhra_frontendengineer-hiringatuber-share-7437760105388990464-5jrr",
            "text": "Frontend Engineer hiring at Uber...",
            "creator_name": "Komal Mundhra",
            "likes": 1200,
            "comments": 80
        }
    ]

    async with async_session() as session:
        repo = CreatorRepository(session)
        user_result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = user_result.scalar()
        
        if not user_id:
            print("No users found. Cannot link to an admin user.")
            return

        for data in posts_data:
            creator_id_hex = data["urn"].split(":")[-1][:8]
            try:
                # Need to use TrackedCreator model directly first
                new_creator = TrackedCreator(
                    user_id=user_id,
                    profile_url=f"https://www.linkedin.com/in/{creator_id_hex}",
                    linkedin_id=f"discovered-{creator_id_hex}",
                    full_name=data["creator_name"]
                )
                creator = await repo.add_tracked_creator(new_creator)
                
                post = IngestedPost(
                    tracked_creator_id=creator.id,
                    linkedin_post_id=data["urn"],
                    post_url=data["url"],
                    content=data["text"],
                    posted_at=datetime.now().replace(tzinfo=None),
                    likes=data["likes"],
                    comments=data["comments"],
                    ingestion_source="direct"
                )
                await repo.add_ingested_post(post)
                # Ensure it saves before exiting
                await session.commit()
                print(f"[+] Successfully injected {data['urn']} into db!")
            except Exception as e:
                print(f"[-] Error injecting {data['urn']}: {e}")

if __name__ == "__main__":
    asyncio.run(inject_posts())
