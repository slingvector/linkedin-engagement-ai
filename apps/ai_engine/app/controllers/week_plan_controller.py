"""
Week Plan webhook controller — AI Engine V2
POST /webhooks/v2/generate/week-plan
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.services.llm_service import LLMService
from app.services.week_plan_service import WeekPlanService, WeekPlanRequest, WeekPlanResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/v2/generate", tags=["v2-week-plan"])


@router.post("/week-plan", response_model=WeekPlanResponse)
async def webhook_generate_week_plan(
    request: WeekPlanRequest,
    api_key: str = Depends(verify_api_key),
) -> WeekPlanResponse:
    """
    Generate a balanced weekly content plan from user-defined pillars.

    Secured via X-AI-API-Key header.
    Returns: {"posts": [{pillar, format, topic, hook, body, cta}]}
    """
    logger.info("week_plan_webhook_called", user_id=request.user_id)
    llm_service = LLMService()
    service = WeekPlanService(llm_service)
    return await service.generate_week_plan(request)
