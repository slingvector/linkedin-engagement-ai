import asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings, get_yaml_config
from app.models.user import User
import os

async def setup():
    settings = get_settings()
    yaml_config = get_yaml_config()
    
    # Use the database URL from settings
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    li_at = yaml_config.get("ingestion", {}).get("scraper", {}).get("linkedin_li_at_cookie")
    if not li_at:
        print("No li_at cookie found in config.yaml")
        return

    # Generate or use existing Fernet key
    # If it's already in the env, use it.
    key_str = os.getenv("FERNET_KEY")
    if not key_str:
        key = Fernet.generate_key()
        key_str = key.decode()
    else:
        key = key_str.encode()
        
    fernet = Fernet(key)
    
    async with async_session() as session:
        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "test@example.com"))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="test@example.com",
                full_name="Test User",
                linkedin_id="test_id_123",
                subscription_tier="pro"
            )
            session.add(user)
        
        user.li_at_cookie_encrypted = fernet.encrypt(li_at.encode()).decode()
        await session.commit()
        print(f"✅ User setup complete. ID: {user.id}")
        print(f"FERNET_KEY={key_str}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup())
