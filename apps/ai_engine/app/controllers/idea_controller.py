"""
Idea generation webhook controller.
Endpoint: POST /webhooks/generate/ideas
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.schemas.idea_schemas import IdeaGenerationRequest, IdeaGenerationResponse
from app.services.llm_service import LLMService
from app.services.idea_service import IdeaService

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/generate", tags=["idea_generation"])


@router.post("/ideas", response_model=IdeaGenerationResponse)
async def webhook_generate_ideas(
    request: IdeaGenerationRequest,
    api_key: str = Depends(verify_api_key),
) -> IdeaGenerationResponse:
    """
    Generate 5 distinct content ideas for an audience and niche.

    Secured via X-AI-API-Key header.
    Returns: {"items": [{"idea": "...", "angle": "..."}]}
    """
    logger.info(
        "idea_generation_requested",
        user_id=request.user_id,
        audience=request.target_audience,
        niche=request.topic_niche,
    )

    llm_service = LLMService()
    idea_service = IdeaService(llm_service)
    result = await idea_service.generate_ideas(request)

    return result
