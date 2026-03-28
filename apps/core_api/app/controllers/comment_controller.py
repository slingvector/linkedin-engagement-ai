import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import difflib

from app.dependencies import get_current_user, get_db
from app.models.feedback import CommentFeedback
from app.models.llmops import ShadowActionLog
from app.schemas.comment import CommentFeedbackCreate

logger = structlog.get_logger()
router = APIRouter(prefix="/comments", tags=["Comments"])

@router.post("/feedback")
async def capture_comment_feedback(
    request: CommentFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Capture user interaction with an AI-generated comment.
    Used to build a training data moat for future LLM fine-tuning.
    """
    feedback = CommentFeedback(
        post_id=request.post_id,
        original_generated_comment=request.original_generated_comment,
        final_user_edited_comment=request.final_user_edited_comment,
        was_used=request.was_used,
        engagement_likes=request.engagement_likes,
        engagement_replies=request.engagement_replies,
    )
    db.add(feedback)
    
    # Calculate similarity score (1.0 = exact match, 0.0 = completely different)
    similarity = difflib.SequenceMatcher(
        None, 
        request.original_generated_comment or "", 
        request.final_user_edited_comment or ""
    ).ratio()
    
    # Also log to LLMOps Data Flywheel
    shadow_log = ShadowActionLog(
        user_id=current_user.id,
        action_type="comment_generation",
        ai_draft_content=request.original_generated_comment,
        human_final_content=request.final_user_edited_comment,
        edit_similarity_score=similarity
    )
    db.add(shadow_log)
    
    await db.commit()
    
    # Optional observability logging
    logger.info(
        "comment_feedback_received", 
        user_id=str(current_user.id),
        post_id=request.post_id,
        was_used=request.was_used,
        edit_similarity=round(similarity, 3)
    )
    
    return {"status": "success", "message": "Feedback captured"}
