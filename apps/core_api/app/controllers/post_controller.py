"""
Post controller — HTTP layer for post generation and management.
Endpoints: generate, list, get, update, delete.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.schemas.post import (
    PostGenerateRequest,
    PostListResponse,
    PostResponse,
    PostUpdateRequest,
    PostScheduleRequest,
)
from app.services.post_service import PostService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_post_service(db: AsyncSession = Depends(get_db)) -> PostService:
    """DI: create a PostService with its repository."""
    return PostService(PostRepository(db))


@router.post("/generate", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def generate_post(
    request: PostGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> PostResponse:
    """
    Generate a new LinkedIn post using AI.

    Flow: Frontend → Core API → AI Engine webhook → LLM → structured response → save draft.
    Requires authentication via Bearer token.
    """
    try:
        post = await service.generate_post(current_user.id, request)
        return PostResponse.model_validate(post)
    except Exception as e:
        logger.error(
            "post_generation_failed",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Post generation failed. The AI Engine may be unavailable.",
        )


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    post_status: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> PostListResponse:
    """List the current user's posts with pagination."""
    posts, total = await service.list_posts(
        current_user.id, page, per_page, post_status
    )
    return PostListResponse(
        posts=[PostResponse.model_validate(p) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> PostResponse:
    """Get a single post by ID."""
    post = await service.get_post(post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    update: PostUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> PostResponse:
    """Update a post draft (edit content or change status)."""
    post = await service.update_post(post_id, current_user.id, update)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)


@router.patch("/{post_id}/schedule", response_model=PostResponse)
async def schedule_post(
    post_id: UUID,
    request: PostScheduleRequest,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> PostResponse:
    """Schedule a post draft for publishing."""
    post = await service.schedule_post(post_id, current_user.id, request.scheduled_at)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(_get_post_service),
) -> None:
    """Soft-delete a post."""
    deleted = await service.delete_post(post_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
