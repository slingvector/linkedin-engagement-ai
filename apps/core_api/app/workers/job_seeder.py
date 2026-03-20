import asyncio
import random
import uuid
import structlog
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import _async_session
from app.models.career import Job

logger = structlog.get_logger()

MOCK_JOBS = [
    {
        "company": "Anthropic",
        "role": "Prompt Engineer",
        "description": "We are seeking a seasoned prompt engineer to evaluate and red-team Claude 3.5 models. You will help tune the system prompts for alignment and creativity.",
        "location": "San Francisco, CA (Hybrid)",
        "salary": "$150k - $240k"
    },
    {
        "company": "Stripe",
        "role": "Backend Software Engineer",
        "description": "Join our global payments infrastructure team. Solid background in Go or Ruby desired. Must have deep understanding of distributed systems and financial ledgers.",
        "location": "Remote - US",
        "salary": "$180k - $280k"
    },
    {
        "company": "Vercel",
        "role": "Frontend Developer (Next.js)",
        "description": "Looking for experts in React, Server Components, and Edge caching to help us build the next iteration of our hosting dashboard.",
        "location": "New York, NY",
        "salary": "$140k - $210k"
    },
    {
        "company": "Supabase",
        "role": "PostgreSQL Performance Architect",
        "description": "Help us manage thousands of clustered PostgreSQL DBs. Required: C, pgvector, WAL tuning, query optimization strategies.",
        "location": "Berlin, Germany",
        "salary": "€100k - €150k"
    },
    {
        "company": "OpenAI",
        "role": "Developer Relations Engineer",
        "description": "Act as the bridge between developers and our product team. Build tutorials, hackathon boilerplates, and represent OpenAI APIs.",
        "location": "San Francisco, CA",
        "salary": "$170k - $250k"
    }
]

async def sync_remote_job_board():
    """
    Mock worker replacing the IIE Playwright Interceptor.
    Checks our DB, if empty or low on jobs, populates it over time.
    """
    while True:
        try:
            async with _async_session() as db:
                # Check DB table size
                result = await db.execute(select(Job).limit(10))
                existing_jobs = result.scalars().all()
                
                # We want a pool of around 5-10 jobs for the demo Feed UI
                if len(existing_jobs) < len(MOCK_JOBS):
                    for mock_job in MOCK_JOBS:
                        # Ensure we don't insert duplicate mock URLs
                        mock_url = f"https://mock-job-board.com/req/{mock_job['company'].lower()}-{str(uuid.uuid4())[:8]}"
                        
                        # Just insert without strict dedupe logic since it's a small mock list
                        # Simple check if company+role exists to avoid bloat across restarts
                        exists = await db.execute(
                            select(Job).where(
                                Job.company_name == mock_job["company"], 
                                Job.role_title == mock_job["role"]
                            )
                        )
                        if not exists.scalars().first():
                            j = Job(
                                company_name=mock_job["company"],
                                role_title=mock_job["role"],
                                description=mock_job["description"],
                                location=mock_job["location"],
                                salary_range=mock_job["salary"],
                                job_url=mock_url,
                                match_score=random.uniform(60.0, 99.0) # Mock scoring
                            )
                            db.add(j)
                    
                    await db.commit()
                    logger.info("job_seeder_injected", added=len(MOCK_JOBS))
                    
        except asyncio.CancelledError:
            logger.info("job_seeder_cancelled")
            break
        except Exception as e:
            logger.error("job_seeder_exception", error=str(e))
        
        # Sleep for an hour or so, since jobs don't spawn instantly
        await asyncio.sleep(3600)
