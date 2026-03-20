"""
Comment generation webhook controller.
Endpoint: POST /webhooks/generate/comments
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.schemas.comment_schemas import CommentGenerationRequest, CommentGenerationResponse
from app.services.llm_service import LLMService
from app.services.comment_service import CommentService

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/generate", tags=["comment_generation"])


@router.post("/comments", response_model=CommentGenerationResponse)
async def webhook_generate_comments(
    request: CommentGenerationRequest,
    api_key: str = Depends(verify_api_key),
) -> CommentGenerationResponse:
    """
    Generate 3 distinct comment strategies for a LinkedIn post.

    Secured via X-AI-API-Key header — only callable by Core API.
    Returns: {comment_insightful, comment_contrarian, comment_supportive}
    """
    logger.info(
        "comment_generation_requested",
        user_id=request.user_id,
        creator=request.creator_name,
        post_length=len(request.post_content),
    )

    llm_service = LLMService()
    comment_service = CommentService(llm_service)
    result = await comment_service.generate_comments(request)

    return result
