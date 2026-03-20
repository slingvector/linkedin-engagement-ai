from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.llmops import ShadowActionLog, LLMEvaluation

router = APIRouter(prefix="/llmops", tags=["llmops"])

@router.get("/metrics")
async def get_safety_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns global safety, reliability, and human-edit similarity datasets plotting into the React LLMOps Dashboard.
    """
    logs_result = await db.execute(
        select(ShadowActionLog)
        .where(ShadowActionLog.user_id == current_user.id)
        .order_by(ShadowActionLog.logged_at.desc())
        .limit(25)
    )
    logs = logs_result.scalars().all()
    
    # Calculate simple global similarity moving average
    total_sim = 0
    evals = []
    
    for log in logs:
        total_sim += (log.edit_similarity_score or 0)
        
        # Get attached LLM evaluation
        eval_res = await db.execute(select(LLMEvaluation).where(LLMEvaluation.log_id == log.id))
        ev = eval_res.scalars().first()
        if ev:
            evals.append({
                "log_id": log.id,
                "action": log.action_type,
                "ai_draft": log.ai_draft_content,
                "human_edit": log.human_final_content,
                "distance": log.edit_similarity_score,
                "hallucination_score": ev.hallucination_score,
                "tone_score": ev.tone_adherence_score,
                "safety_score": ev.safety_compliance_score,
                "rationale": ev.judge_rationale
            })

    avg_similarity = total_sim / len(logs) if logs else 1.0

    return {
        "status": "success", 
        "data": {
            "global_human_acceptance_rate": avg_similarity,
            "total_telemetry_events": len(logs),
            "recent_evaluations": evals
        }
    }
