import asyncio
from app.dependencies import _engine as engine
from app.models.base import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import *

async def init_career_db():
    print("Creating career tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Career database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_career_db())
