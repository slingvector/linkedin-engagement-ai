import asyncio
import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.creator import IngestedPost, TrackedCreator
from app.config import get_settings

logger = structlog.get_logger()

async def purge_corrupted_data():
    """
    Identifies and removes fsd_notificationCard posts and the 
    subsequent 'dummy' creators that were auto-created for them.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Identify corrupted posts
        result = await session.execute(
            select(IngestedPost)
            .where(IngestedPost.linkedin_post_id.contains("notificationCard"))
        )
        corrupted_posts = result.scalars().all()
        
        if not corrupted_posts:
            print("[+] No corrupted posts found. Database is already clean.")
            return

        print(f"[!] Found {len(corrupted_posts)} corrupted notification posts. Starting purge...")
        
        creator_ids_to_check = set()
        for post in corrupted_posts:
            creator_ids_to_check.add(post.tracked_creator_id)
            print(f"    [-] Deleting Post: {post.linkedin_post_id}")
            await session.delete(post)
        
        await session.flush()
        
        # 2. Check for "Dummy Creators" that have no other (valid) posts remaining
        # and match the "Viral Creator {urn-suffix}" or "LinkedIn User ..." pattern
        for creator_id in creator_ids_to_check:
            # Check if this creator has any legitimate posts remaining
            post_check = await session.execute(
                select(IngestedPost).where(IngestedPost.tracked_creator_id == creator_id)
            )
            remaining_posts = post_check.scalars().all()
            
            if not remaining_posts:
                creator_result = await session.execute(
                    select(TrackedCreator).where(TrackedCreator.id == creator_id)
                )
                creator = creator_result.scalar_one_or_none()
                
                if creator and ("LinkedIn User" in creator.full_name or "Viral Creator" in creator.full_name):
                    print(f"    [-] Deleting Dummy Creator: {creator.full_name} ({creator.id})")
                    await session.delete(creator)

        print("[+] Committing changes...")
        await session.commit()
        print("[+] Purge complete. 100% clean.")

if __name__ == "__main__":
    asyncio.run(purge_corrupted_data())
