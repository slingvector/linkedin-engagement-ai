import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.config import get_settings
from app.models.user import User
from app.utils.security import create_jwt_token
import uuid

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="devuser@example.com",
                full_name="Dev Tester",
                linkedin_id="dev_id",
                subscription_tier="pro"
            )
            session.add(user)
            await session.commit()

        token = create_jwt_token({"sub": str(user.id), "email": user.email})
        print("\n" + "="*30)
        print("YOUR DEV JWT TOKEN:")
        print(token)
        print("="*30 + "\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
