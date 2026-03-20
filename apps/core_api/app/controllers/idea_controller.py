"""
Idea controller — proxies the idea generation calls to the AI Engine.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.schemas.post import IdeaGenerateRequest, IdeaGenerateResponse
from app.services.post_service import PostService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter(prefix="/ideas", tags=["ideas"])


def _get_post_service(db: AsyncSession = Depends(get_db)) -> PostService:
    """DI: create a PostService."""
    return PostService(PostRepository(db))


@router.post("/generate", response_model=IdeaGenerateResponse, status_code=status.HTTP_200_OK)
async def generate_ideas(
    request: IdeaGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> IdeaGenerateResponse:
    """
    Generate 5 LinkedIn post ideas/angles.
    """
    try:
        return await service.generate_ideas(current_user.id, request)
    except Exception as e:
        logger.error(
            "idea_generation_failed",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Idea generation failed. The AI Engine may be unavailable.",
        )
