"""
V2 Analytics Controller — Posting Heatmap
Provides GET /api/v2/analytics/heatmap for the calendar UI.
"""

from fastapi import APIRouter, Depends, Query, status
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.heatmap_service import HeatmapService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v2/analytics",
    tags=["v2-analytics"],
    dependencies=[Depends(get_current_user)],
)


def get_heatmap_service(db: AsyncSession = Depends(get_db)) -> HeatmapService:
    return HeatmapService(db)


@router.get(
    "/heatmap",
    status_code=status.HTTP_200_OK,
    summary="Posting time engagement heatmap",
    description=(
        "Returns a DOW × hour engagement heatmap for the calendar grid overlay. "
        "Values are normalised 0.0–1.0. Falls back to LinkedIn global benchmarks "
        "when the user has fewer than 5 published posts with impression data."
    ),
)
async def get_heatmap(
    weeks: int = Query(default=8, ge=1, le=52, description="Lookback window in weeks"),
    current_user: User = Depends(get_current_user),
    service: HeatmapService = Depends(get_heatmap_service),
):
    """
    Response shape:
    {
      heatmap: { monday: { "10": 0.94, ... }, tuesday: {...}, ... },
      best_slots: [{ day, hour, avg_engagement_rate }],
      worst_slots: [{ day, hour, avg_engagement_rate }],
      data_source: "personal" | "global_benchmark",
      sample_size: int
    }
    """
    logger.info("heatmap_requested", user_id=str(current_user.id), weeks=weeks)
    return await service.get_heatmap(current_user.id, weeks=weeks)
