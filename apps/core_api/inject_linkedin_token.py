import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from cryptography.fernet import Fernet
from app.config import get_settings

async def inject_token():
    settings = get_settings()
    fernet = Fernet(settings.fernet_key.encode())
    dummy_token = "AQVm-fake-linkedin-token-for-dev-testing"
    encrypted_token = fernet.encrypt(dummy_token.encode()).decode()

    engine = create_async_engine(str(settings.database_url), echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        await session.execute(
            text("""
            UPDATE users 
            SET write_access_token_encrypted = :token, linkedin_person_id = 'urn:li:person:dummy123'
            WHERE email = 'devuser@example.com'
            """)
            , {"token": encrypted_token}
        )
        await session.commit()
    print("Injected dummy LinkedIn token!")

if __name__ == "__main__":
    asyncio.run(inject_token())
