"""
Virality Score webhook controller — AI Engine V2
POST /webhooks/v2/score/post
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.services.llm_service import LLMService
from app.services.virality_score_service import (
    ViralityScoreService, ScoreRequest, ScoreResponse
)

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/v2/score", tags=["v2-virality"])


@router.post("/post", response_model=ScoreResponse)
async def webhook_score_post(
    request: ScoreRequest,
    api_key: str = Depends(verify_api_key),
) -> ScoreResponse:
    """
    Score a LinkedIn draft post 0-100 with breakdown and hook alternatives.

    Secured via X-AI-API-Key header.
    Returns: {total_score, breakdown, hook_alternatives, reasoning}
    """
    logger.info("score_webhook_called", user_id=request.user_id, post_id=request.post_id)
    llm_service = LLMService()
    service = ViralityScoreService(llm_service)
    return await service.score_post(request)
