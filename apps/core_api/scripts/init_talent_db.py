import asyncio
import logging

from app.database import engine
from app.models.talent import Candidate, Requisition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_talent_tables():
    logger.info("Initializing phase 5 talent and ATS database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Candidate.metadata.create_all)
        await conn.run_sync(Requisition.metadata.create_all)
    logger.info("Talent and ATS tables successfully created!")

if __name__ == "__main__":
    asyncio.run(init_talent_tables())
