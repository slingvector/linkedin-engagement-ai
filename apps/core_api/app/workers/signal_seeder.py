import asyncio
import json
import random
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import _async_session as AsyncSessionLocal
from app.models.base import Base
from app.models.user import User
from app.models.enterprise import TargetAccount, CompanySignal

logger = logging.getLogger(__name__)

MOCK_COMPANIES = [
    {
        "company_name": "Acme Corp",
        "industry": "B2B SaaS",
        "employee_count": "500-1000",
        "domain": "acme.io"
    },
    {
        "company_name": "Zephyr Logistics",
        "industry": "Supply Chain",
        "employee_count": "1000-5000",
        "domain": "zephyrlogistics.com"
    },
    {
        "company_name": "Globex Financial",
        "industry": "Fintech",
        "employee_count": "200-500",
        "domain": "globex.finance"
    },
    {
        "company_name": "Initech",
        "industry": "Software Consulting",
        "employee_count": "1000+",
        "domain": "initech.net"
    }
]

MOCK_SIGNALS = [
    {
        "signal_type": "funding_round",
        "signal_description": "Just closed a $50M Series B led by Sequoia Capital to scale their engineering teams."
    },
    {
        "signal_type": "leadership_change",
        "signal_description": "Hired a new VP of Engineering from Google to overhaul their legacy monolith."
    },
    {
        "signal_type": "office_expansion",
        "signal_description": "Opening a massive new European headquarters in Dublin, Ireland."
    },
    {
        "signal_type": "product_launch",
        "signal_description": "Announced the release of their next-gen AI analytics suite at TechCrunch Disrupt."
    }
]

async def seed_enterprise_signals_loop():
    """
    Simulates a background process intercepting B2B triggers (e.g., crunchbase webhooks/news).
    """
    logger.info("Starting Enterprise ABM Signal Seeder Background Worker...")
    
    while True:
        try:
            await asyncio.sleep(40) # Wait 40s between simulated discoveries
            async with AsyncSessionLocal() as session:
                # Find the user
                result = await session.execute(select(User).limit(1))
                user = result.scalar_one_or_none()
                
                if user:
                    mock_company = random.choice(MOCK_COMPANIES)
                    
                    # Ensure account exists or create it
                    acct_result = await session.execute(
                        select(TargetAccount).where(
                            TargetAccount.user_id == user.id, 
                            TargetAccount.company_name == mock_company["company_name"]
                        )
                    )
                    account = acct_result.scalars().first()
                    
                    if not account:
                        account = TargetAccount(
                            user_id=user.id,
                            company_name=mock_company["company_name"],
                            industry=mock_company["industry"],
                            employee_count=mock_company["employee_count"],
                            domain=mock_company["domain"],
                            abm_status="watching"
                        )
                        session.add(account)
                        await session.commit()
                        await session.refresh(account)
                    
                    # Generate a random trigger event for the account
                    mock_signal = random.choice(MOCK_SIGNALS)
                    signal = CompanySignal(
                        account_id=account.id,
                        signal_type=mock_signal["signal_type"],
                        signal_description=mock_signal["signal_description"]
                    )
                    session.add(signal)
                    await session.commit()
                    logger.info(f"Seeder Process logged new Enterprise Signal for {account.company_name}: {signal.signal_type}")

        except Exception as e:
            logger.error(f"Enterprise Signal Seeder encountered error: {e}")
            await asyncio.sleep(5)
