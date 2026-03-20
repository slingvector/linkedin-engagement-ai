from fastapi import APIRouter, Depends, status, HTTPException, Body
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.sales import Prospect, Conversation

logger = structlog.get_logger()

router = APIRouter(
    prefix="/sales",
    tags=["Sales CRM"],
)

@router.get("/prospects")
async def list_prospects(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns all prospects intercepted by the lead seeder for the current user.
    """
    result = await db.execute(
        select(Prospect)
        .where(Prospect.user_id == current_user.id)
        .order_by(Prospect.created_at.desc())
    )
    prospects = result.scalars().all()
    
    return {
        "data": [
            {
                "id": str(p.id),
                "name": p.name,
                "headline": p.headline,
                "company": p.company,
                "intent_score": p.intent_score,
                "buying_signal": p.buying_signal,
                "created_at": p.created_at
            }
            for p in prospects
        ]
    }

@router.put("/prospects/{id}/status", status_code=status.HTTP_200_OK)
async def update_prospect_conversation_status(
    id: str,
    status_val: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the Kanban status of a sales conversation (e.g. Lead -> Contacted -> Won).
    Since we isolated conversations from prospects, we map the Prospect ID to its Conversation.
    """
    valid_statuses = ["new_lead", "contacted", "qualified", "closed_won", "closed_lost"]
    if status_val not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid sales pipeline status.")
        
    # Check if a conversation exists for this prospect. If not, create one.
    conv_result = await db.execute(
        select(Conversation).where(Conversation.prospect_id == id, Conversation.user_id == current_user.id)
    )
    conversation = conv_result.scalars().first()
    
    if not conversation:
        # Verify prospect exists before creating a convo
        prospect_check = await db.execute(select(Prospect).where(Prospect.id == id, Prospect.user_id == current_user.id))
        if not prospect_check.scalars().first():
            raise HTTPException(status_code=404, detail="Prospect not found.")
            
        conversation = Conversation(
            user_id=current_user.id,
            prospect_id=id,
            status=status_val
        )
        db.add(conversation)
    else:
        conversation.status = status_val
        
    await db.commit()
    return {"message": "Pipeline status updated successfully."}
