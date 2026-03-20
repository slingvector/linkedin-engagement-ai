import asyncio
from app.dependencies import _engine as engine
from app.models.base import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import *

async def init_db():
    print("Creating newly added analytics tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/updated successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
