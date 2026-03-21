import asyncio
import os
import structlog
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.config import get_settings
from app.models.user import User

logger = structlog.get_logger()

# Hardcoded test Fernet key for the test script (In prod, grab from ENV)
TEST_ENCRYPTION_KEY = Fernet.generate_key()

async def create_test_user():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    email = input("Enter Real Test Email: ")
    linkedin_id = input("Enter LinkedIn Profiling ID (or random): ") or uuid4().hex[:10]
    full_name = input("Enter Full Name: ")
    li_at_cookie = input("Enter LinkedIn 'li_at' session cookie (optional): ")
    
    fernet = Fernet(TEST_ENCRYPTION_KEY)
    
    async with async_session() as session:
        user = User(
            email=email,
            full_name=full_name,
            linkedin_id=linkedin_id,
            subscription_tier="pro",
        )
        
        if li_at_cookie:
            user.li_at_cookie_encrypted = fernet.encrypt(li_at_cookie.encode()).decode()
            
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(
            "test_user_created", 
            user_id=str(user.id), 
            email=email,
            encryption_key=TEST_ENCRYPTION_KEY.decode()
        )
        print(f"\n✅ User Created Successfully! UUID: {user.id}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_user())
