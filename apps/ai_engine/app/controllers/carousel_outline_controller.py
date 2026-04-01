"""
Carousel Outline webhook controller — AI Engine V2
POST /webhooks/v2/generate/carousel-outline
"""

from fastapi import APIRouter, Depends
import structlog

from app.dependencies import verify_api_key
from app.services.llm_service import LLMService
from app.services.carousel_outline_service import (
    CarouselOutlineService, CarouselOutlineRequest, CarouselOutlineResponse
)

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/v2/generate", tags=["v2-carousel"])


@router.post("/carousel-outline", response_model=CarouselOutlineResponse)
async def webhook_generate_carousel_outline(
    request: CarouselOutlineRequest,
    api_key: str = Depends(verify_api_key),
) -> CarouselOutlineResponse:
    """
    Generate a 7-slide LinkedIn carousel outline.

    Slide 1: scroll-stopping hook
    Slides 2–6: one actionable insight per slide
    Slide 7: CTA + next-carousel teaser

    Returns: {slides, cover_hook, cta_slide_text}
    Secured via X-AI-API-Key header.
    """
    logger.info(
        "carousel_outline_webhook_called",
        user_id=request.user_id,
        topic=request.topic,
    )
    llm_service = LLMService()
    service = CarouselOutlineService(llm_service)
    return await service.generate_outline(request)
