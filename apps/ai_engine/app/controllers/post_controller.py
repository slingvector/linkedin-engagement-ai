"""
Post generation webhook controller.
Endpoint: POST /webhooks/generate/post
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.schemas.post_schemas import PostGenerationRequest, PostGenerationResponse
from app.services.llm_service import LLMService
from app.services.post_service import PostService

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/generate", tags=["post_generation"])


@router.post("/post", response_model=PostGenerationResponse)
async def webhook_generate_post(
    request: PostGenerationRequest,
    api_key: str = Depends(verify_api_key),
) -> PostGenerationResponse:
    """
    Generate a structured LinkedIn post using the specified framework.

    Secured via X-AI-API-Key header — only callable by Core API.
    Returns: {hook, body_content, call_to_action}
    """
    logger.info(
        "post_generation_requested",
        user_id=request.user_id,
        framework=request.framework,
        topic=request.topic[:50],
    )

    llm_service = LLMService()
    post_service = PostService(llm_service)
    result = await post_service.generate_post(request)

    return result
