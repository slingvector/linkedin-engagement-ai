import asyncio
import random
import uuid
import structlog
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import _async_session
from app.models.sales import Prospect

logger = structlog.get_logger()

MOCK_LEADS = [
    {
        "name": "Alex Mercer",
        "headline": "VP of Engineering at DataSystems Inc",
        "company": "DataSystems Inc",
        "buying_signal": "Just saw your post on Kubernetes scaling. We're hitting a wall with our current provider. Do you do consulting?",
    },
    {
        "name": "Sarah Chen",
        "headline": "SDR Manager @ RevenueGrid",
        "company": "RevenueGrid",
        "buying_signal": "What tool are you using to generate these personalized videos? My team could use this.",
    },
    {
        "name": "Marcus Johnson",
        "headline": "Founder & CEO, BuildRight",
        "company": "BuildRight",
        "buying_signal": "Great insights. Pricing?",
    },
    {
        "name": "Elena Rodriguez",
        "headline": "Product Lead",
        "company": "Fintech Solutions",
        "buying_signal": "We tried building this internally and failed. Would love to see a demo.",
    },
    {
        "name": "David Wu",
        "headline": "CTO at Stealth Startup",
        "company": "Stealth Startup",
        "buying_signal": "Followed. How does this compare to conventional enterprise solutions?",
    }
]

async def seed_leads_loop():
    """Simulates an active Playwright worker scraping high-intent comments off targeted competitors."""
    logger.info("lead_seeder_started", mock_count=len(MOCK_LEADS))
    
    while True:
        try:
            # Random wait (10 to 30 seconds)
            await asyncio.sleep(random.randint(10, 30))
            
            async with _async_session() as session:
                # Get a primary user to bind the leads to (we assume the ID exists from UI creation)
                from app.models.user import User
                user_res = await session.execute(select(User).limit(1))
                user = user_res.scalars().first()
                
                if user:
                    lead_data = random.choice(MOCK_LEADS)
                    
                    # See if this user already has this lead (we'll just use name as proxy)
                    existing = await session.execute(
                        select(Prospect).where(Prospect.user_id == user.id, Prospect.name == lead_data["name"])
                    )
                    
                    if not existing.scalars().first():
                        # The IIE "intercepted" a new lead. We store it.
                        new_lead = Prospect(
                            user_id=user.id,
                            name=lead_data["name"],
                            headline=lead_data["headline"],
                            company=lead_data["company"],
                            buying_signal=lead_data["buying_signal"],
                            # Intentionally leaving intent_score at 0 for now. 
                            # The AI Webhook will parse this and enrich it!
                        )
                        session.add(new_lead)
                        await session.commit()
                        logger.info("new_lead_seeded", name=new_lead.name, prospect_id=str(new_lead.id))
                        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("lead_seeder_error", error=str(e))
            await asyncio.sleep(5)
