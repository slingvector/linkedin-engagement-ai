import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.feedback import CommentFeedback
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
    await db.commit()
    
    # Optional observability logging
    logger.info(
        "comment_feedback_received", 
        user_id=str(current_user.id),
        post_id=request.post_id,
        was_used=request.was_used
    )
    
    return {"status": "success", "message": "Feedback captured"}
