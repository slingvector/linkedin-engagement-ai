from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.enterprise import TargetAccount, CompanySignal, Campaign

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

@router.get("/signals")
async def list_active_signals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns Target Accounts and associated Signal triggers for the Radar UI.
    """
    # Fetch accounts representing ABM targets
    acct_result = await db.execute(
        select(TargetAccount)
        .where(TargetAccount.user_id == current_user.id)
        .order_by(TargetAccount.created_at.desc())
    )
    accounts = acct_result.scalars().all()
    
    # Bundle internal signals for return mapping
    response_data = []
    for account in accounts:
        sig_result = await db.execute(
            select(CompanySignal)
            .where(CompanySignal.account_id == account.id)
            .order_by(CompanySignal.discovered_at.desc())
        )
        signals = sig_result.scalars().all()
        response_data.append({
            "account": account,
            "signals": signals
        })
        
    return {"status": "success", "data": response_data}

@router.post("/campaigns")
async def create_outbound_campaign(
    campaign_data: dict, # expecting {"name": "C-Suite Push", "account_id": "uuid"}
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new draft Multi-Touch generative outbound sequence container for an Account.
    """
    account_id = campaign_data.get("account_id")
    name = campaign_data.get("name", "Generated Sequence")
    
    if not account_id:
        raise HTTPException(status_code=400, detail="Must provide account_id")
        
    campaign = Campaign(
        account_id=account_id,
        name=name,
        status="drafting"
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    return {"status": "success", "data": campaign}
