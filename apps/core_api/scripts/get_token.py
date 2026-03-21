import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

engine = create_async_engine("postgresql+asyncpg://postgres:changeme_local_only@localhost:5432/linkedin_saas")
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def retrieve_token():
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        auth_service = AuthService(user_repo)
        try:
            tokens = await auth_service.login("admin@cortex.com", "password123")
            print("JWT_ACCESS_TOKEN:", tokens.access_token)
        except Exception as e:
            print("LOGIN ERROR:", e)

if __name__ == "__main__":
    asyncio.run(retrieve_token())
