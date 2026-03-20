from fastapi import APIRouter, Depends, status
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)

def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db))


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """
    Returns time-series impressions data and aggregated demographics pie-chart mappings.
    """
    logger.info("fetching_analytics_dashboard", user_id=str(current_user.id))
    return await service.get_dashboard_metrics(current_user.id)
