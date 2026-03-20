import asyncio
import json
import random
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import _async_session as AsyncSessionLocal
from app.models.base import Base
from app.models.user import User
from app.models.talent import Candidate

logger = logging.getLogger(__name__)

MOCK_CANDIDATES = [
    {
        "name": "Sarah Chen",
        "headline": "Senior Full Stack Engineer @ Stripe | React & Node.js",
        "current_role": "Senior Full Stack Engineer",
        "current_company": "Stripe",
        "skills": json.dumps(["React", "Node.js", "TypeScript", "GraphQL", "PostgreSQL"])
    },
    {
        "name": "Marcus Johnson",
        "headline": "DevOps Architect | AWS Certified | Kubernetes Fanatic",
        "current_role": "Cloud Architect",
        "current_company": "Netflix",
        "skills": json.dumps(["AWS", "Kubernetes", "Docker", "Terraform", "Python", "Go"])
    },
    {
        "name": "Elena Rodriguez",
        "headline": "Frontend Lead Building the future of Web3 at Metamask",
        "current_role": "Frontend Lead",
        "current_company": "ConsenSys",
        "skills": json.dumps(["React", "Web3.js", "Ethers.js", "TailwindCSS", "Next.js"])
    },
    {
        "name": "David Kim",
        "headline": "Data Scientist | ML & AI | Predictive Modeling",
        "current_role": "Data Scientist",
        "current_company": "Google",
        "skills": json.dumps(["Python", "PyTorch", "TensorFlow", "SQL", "Pandas"])
    },
    {
        "name": "Emily Foster",
        "headline": "Product Manager | Driving Growth at Airbnb | Agile & Scrum",
        "current_role": "Senior Product Manager",
        "current_company": "Airbnb",
        "skills": json.dumps(["Product Strategy", "Agile", "Scrum", "Data Analysis", "A/B Testing"])
    }
]

async def seed_candidates_loop():
    """
    Simulates a background process intercepting Network traffic to discover passive candidates.
    Every 30 seconds, it pushes a mock candidate into the database for tracked users.
    """
    logger.info("Starting Candidate Seeder Background Worker...")
    
    while True:
        try:
            await asyncio.sleep(30) # Wait 30s between simulated discoveries
            async with AsyncSessionLocal() as session:
                # Get the first user to simulate seeding for
                result = await session.execute(select(User).limit(1))
                user = result.scalar_one_or_none()
                
                if user:
                    mock_data = random.choice(MOCK_CANDIDATES)
                    
                    # Ensure we don't spam duplicate names
                    exist_check = await session.execute(
                        select(Candidate).where(Candidate.user_id == user.id, Candidate.name == mock_data["name"])
                    )
                    if not exist_check.scalars().first():
                        candidate = Candidate(
                            user_id=user.id,
                            name=mock_data["name"],
                            headline=mock_data["headline"],
                            current_role=mock_data["current_role"],
                            current_company=mock_data["current_company"],
                            skills=mock_data["skills"],
                            ats_status="sourced"
                        )
                        session.add(candidate)
                        await session.commit()
                        logger.info(f"Seeder Process logged new Candidate: {candidate.name}")

        except Exception as e:
            logger.error(f"Candidate Seeder encountered error: {e}")
            await asyncio.sleep(5)
