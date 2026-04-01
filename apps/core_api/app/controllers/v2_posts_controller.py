"""
V2 Posts Controller — Virality Scoring
POST /api/v2/posts/{post_id}/score
GET  /api/v2/posts/{post_id}/score  (return cached score)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.services.virality_service import ViralityService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v2/posts",
    tags=["v2-posts"],
    dependencies=[Depends(get_current_user)],
)


# ── Response schemas ──────────────────────────────────────────────────────────

class ScoreBreakdownResponse(BaseModel):
    hook_strength: int
    readability: int
    value_density: int
    cta_quality: int

class HookAlternativeResponse(BaseModel):
    hook: str
    predicted_score: int

class ViralityScoreResponse(BaseModel):
    post_id: str
    virality_score: int | None
    score_breakdown: ScoreBreakdownResponse | None
    hook_alternatives: list[HookAlternativeResponse]
    score_updated_at: str | None
    message: str


# ── Dependency ────────────────────────────────────────────────────────────────

def get_virality_service(db: AsyncSession = Depends(get_db)) -> ViralityService:
    return ViralityService(PostRepository(db), db)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/{post_id}/score",
    status_code=status.HTTP_200_OK,
    response_model=ViralityScoreResponse,
    summary="Score a post draft for viral potential",
    description=(
        "Calls the AI Engine to score the post 0-100 across hook strength, readability, "
        "value density, and CTA quality. Returns 3 alternative hooks with predicted scores. "
        "Result is persisted to the post record for instant re-fetch."
    ),
)
async def score_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ViralityService = Depends(get_virality_service),
):
    logger.info("virality_score_endpoint_called", post_id=str(post_id), user_id=str(current_user.id))
    try:
        post = await service.score_post(post_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    breakdown = None
    if post.score_breakdown:
        breakdown = ScoreBreakdownResponse(**post.score_breakdown)

    alternatives = [
        HookAlternativeResponse(**h)
        for h in (post.hook_alternatives or [])
    ]

    return ViralityScoreResponse(
        post_id=str(post.id),
        virality_score=post.virality_score,
        score_breakdown=breakdown,
        hook_alternatives=alternatives,
        score_updated_at=post.score_updated_at.isoformat() if post.score_updated_at else None,
        message=f"Virality score: {post.virality_score}/100",
    )


@router.get(
    "/{post_id}/score",
    status_code=status.HTTP_200_OK,
    response_model=ViralityScoreResponse,
    summary="Get cached virality score for a post",
)
async def get_score(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = PostRepository(db)
    post = await repo.get_by_id(post_id, current_user.id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    breakdown = None
    if post.score_breakdown:
        breakdown = ScoreBreakdownResponse(**post.score_breakdown)

    return ViralityScoreResponse(
        post_id=str(post.id),
        virality_score=post.virality_score,
        score_breakdown=breakdown,
        hook_alternatives=[HookAlternativeResponse(**h) for h in (post.hook_alternatives or [])],
        score_updated_at=post.score_updated_at.isoformat() if post.score_updated_at else None,
        message="Cached score" if post.virality_score else "Not scored yet — POST to /score to generate",
    )
