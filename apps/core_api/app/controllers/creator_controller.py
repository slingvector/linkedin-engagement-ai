"""
Creator controller — HTTP endpoints for Creator Radar + Comment Copilot.
"""

from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.creator_repository import CreatorRepository
from app.repositories.comment_repository import CommentDraftRepository
from app.services.creator_service import CreatorService
from app.schemas.creator import (
    TrackedCreatorCreate,
    TrackedCreatorResponse,
    IngestedPostResponse,
    CommentGenerateRequest,
    CommentDraftResponse,
    CommentDraftUpdateRequest,
)

logger = structlog.get_logger()

# Sub-routers for logical separation
radar_router = APIRouter(prefix="/radar", tags=["creator_radar"])
copilot_router = APIRouter(prefix="/copilot", tags=["comment_copilot"])


def _get_creator_service(db: AsyncSession = Depends(get_db)) -> CreatorService:
    """DI for CreatorService."""
    return CreatorService(CreatorRepository(db), CommentDraftRepository(db))


# --- Creator Radar Endpoints ---

@radar_router.post(
    "/creators", 
    response_model=TrackedCreatorResponse, 
    status_code=status.HTTP_201_CREATED
)
async def add_tracked_creator(
    request: TrackedCreatorCreate,
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> TrackedCreatorResponse:
    """Start tracking a new creator."""
    creator = await service.add_tracked_creator(current_user.id, request)
    return TrackedCreatorResponse.model_validate(creator)


@radar_router.get("/creators", response_model=list[TrackedCreatorResponse])
async def list_tracked_creators(
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> list[TrackedCreatorResponse]:
    """List all active tracked creators."""
    creators = await service.list_tracked_creators(current_user.id)
    return [TrackedCreatorResponse.model_validate(c) for c in creators]


@radar_router.delete("/creators/{creator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tracked_creator(
    creator_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> None:
    """Stop tracking a creator."""
    deleted = await service.untrack_creator(creator_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Creator not found")


# --- Comment Copilot Endpoints ---

@copilot_router.get("/feed", response_model=dict[str, Any])
async def get_action_desk_feed(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> dict[str, Any]:
    """
    Get the "Action Desk" feed: recent posts from tracked creators.
    Returns posts with basic creator info attached.
    """
    feed, total = await service.get_action_desk_feed(current_user.id, page, per_page)
    
    # We serialize the joined result manually here for the UI
    items = []
    for item in feed:
        post = item["post"]
        items.append({
            "post": IngestedPostResponse.model_validate(post).model_dump(),
            "creator_name": item["creator_name"],
            "creator_picture": item["creator_picture"],
        })
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@copilot_router.post("/generate", response_model=CommentDraftResponse)
async def generate_comments(
    request: CommentGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> CommentDraftResponse:
    """
    Trigger the AI Engine to generate 3 comment strategies for an ingested post.
    """
    try:
        draft = await service.generate_comments(current_user.id, request)
        return CommentDraftResponse.model_validate(draft)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("comment_generation_failed", error=str(e))
        raise HTTPException(
            status_code=502, 
            detail="Comment generation failed. AI Engine unavailable."
        )


@copilot_router.get("/posts/{ingested_post_id}/drafts", response_model=CommentDraftResponse)
async def get_comment_drafts(
    ingested_post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> CommentDraftResponse:
    """Get the previously generated comment drafts for a post."""
    draft = await service.get_comment_draft(current_user.id, ingested_post_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Drafts not found")
    return CommentDraftResponse.model_validate(draft)


@copilot_router.patch("/posts/{ingested_post_id}/drafts", response_model=CommentDraftResponse)
async def update_comment_draft(
    ingested_post_id: UUID,
    request: CommentDraftUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorService = Depends(_get_creator_service),
) -> CommentDraftResponse:
    """
    Update a draft (e.g., 'Copy & Go' flow — marking a strategy as selected/copied).
    """
    draft = await service.update_comment_draft(current_user.id, ingested_post_id, request)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return CommentDraftResponse.model_validate(draft)
