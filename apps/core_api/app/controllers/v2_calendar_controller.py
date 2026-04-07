"""
V2 Calendar Controller — Smart Fill
POST /api/v2/calendar/smart-fill
"""

from datetime import date as DateType
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, Body
from pydantic import BaseModel, Field
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.schemas.post import PostResponse
from app.services.heatmap_service import HeatmapService
from app.services.smart_fill_service import SmartFillService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v2/calendar",
    tags=["v2-calendar"],
    dependencies=[Depends(get_current_user)],
)


# ── Request schema ────────────────────────────────────────────────────────────

class SmartFillRequest(BaseModel):
    pillars: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Content pillars (topics) to rotate across the week",
        examples=[["AI Automation", "Founder Stories", "Product Lessons"]],
    )
    posts_per_week: int = Field(default=4, ge=1, le=7)
    preferred_formats: list[str] = Field(
        default=["text", "carousel"],
        description="Allowed post formats: text, carousel, video",
    )
    top_posts_sample: list[str] = Field(
        default=[],
        max_length=3,
        description="Hook lines of top-performing past posts for voice calibration",
    )


class SmartFillResponse(BaseModel):
    posts: list[PostResponse]
    message: str


# ── Endpoint ──────────────────────────────────────────────────────────────────

def get_smart_fill_service(db: AsyncSession = Depends(get_db)) -> SmartFillService:
    post_repo = PostRepository(db)
    heatmap_svc = HeatmapService(db)
    return SmartFillService(post_repo, heatmap_svc)


@router.post(
    "/smart-fill",
    status_code=status.HTTP_201_CREATED,
    response_model=SmartFillResponse,
    summary="AI-powered weekly content plan",
    description=(
        "Generates a complete week of LinkedIn post drafts from user-defined content pillars. "
        "Each draft is pre-slotted at the user's optimal posting time based on heatmap data."
    ),
)
async def smart_fill_calendar(
    request: SmartFillRequest,
    current_user: User = Depends(get_current_user),
    service: SmartFillService = Depends(get_smart_fill_service),
):
    logger.info(
        "smart_fill_requested",
        user_id=str(current_user.id),
        pillars=request.pillars,
        posts_per_week=request.posts_per_week,
    )

    posts = await service.smart_fill(
        user_id=current_user.id,
        pillars=request.pillars,
        posts_per_week=request.posts_per_week,
        preferred_formats=request.preferred_formats,
        top_posts_sample=request.top_posts_sample,
    )

    return SmartFillResponse(
        posts=[PostResponse.model_validate(p) for p in posts],
        message=f"Created {len(posts)} draft posts. Drag them on the calendar to adjust timing.",
    )
