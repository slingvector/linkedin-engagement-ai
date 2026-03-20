from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.dependencies import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.talent import Candidate, Requisition

router = APIRouter(prefix="/talent", tags=["talent"])

@router.get("/candidates")
async def list_candidates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the Candidate CRM mapping for the ATS.
    """
    result = await db.execute(
        select(Candidate)
        .where(Candidate.user_id == current_user.id)
        .order_by(Candidate.created_at.desc())
    )
    candidates = result.scalars().all()
    
    return {"status": "success", "data": candidates}

@router.put("/candidates/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: str,
    stage: dict, # Expecting { "stage": "interviewing" } etc
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mutates ATS stage mapping (e.g., sourced -> contacted -> interviewing).
    """
    new_stage = stage.get("stage")
    if not new_stage:
        raise HTTPException(status_code=400, detail="Missing stage string")

    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.user_id == current_user.id)
    )
    candidate = result.scalars().first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    candidate.ats_status = new_stage
    await db.commit()
    await db.refresh(candidate)
    
    return {"status": "success", "data": candidate}
