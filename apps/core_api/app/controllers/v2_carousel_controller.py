"""
V2 Carousel Controller — Core API
POST /api/v2/posts/{post_id}/carousel          → generate carousel outline + render PDF
GET  /api/v2/posts/{post_id}/carousel          → fetch most recent CarouselAsset
POST /api/v2/posts/{post_id}/carousel/publish  → LinkedIn 3-step Document Upload
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.post_repository import PostRepository
from app.services.carousel_service import CarouselService
from app.utils.security import decrypt_token

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v2/posts",
    tags=["v2-carousel"],
    dependencies=[Depends(get_current_user)],
)


# ── Response schemas ───────────────────────────────────────────────────────────

class SlideResponse(BaseModel):
    slide_number: int
    headline: str
    body: str
    visual_suggestion: str


class CarouselAssetResponse(BaseModel):
    id: str
    post_id: str
    slide_count: int
    slides: list[SlideResponse]
    pdf_url: str | None
    status: str
    linkedin_asset_urn: str | None
    brand_kit: dict | None
    created_at: str


class PublishCarouselRequest(BaseModel):
    post_text: str  # The LinkedIn post caption to accompany the carousel


class PublishCarouselResponse(BaseModel):
    linkedin_post_urn: str
    message: str


# ── Dependency ─────────────────────────────────────────────────────────────────

def get_carousel_service(db: AsyncSession = Depends(get_db)) -> CarouselService:
    return CarouselService(PostRepository(db), db)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _asset_to_response(asset) -> CarouselAssetResponse:
    slides = [
        SlideResponse(
            slide_number=s.get("slide_number", i + 1),
            headline=s.get("headline", ""),
            body=s.get("body", ""),
            visual_suggestion=s.get("visual_suggestion", ""),
        )
        for i, s in enumerate(asset.slides_json or [])
    ]
    return CarouselAssetResponse(
        id=str(asset.id),
        post_id=str(asset.post_id),
        slide_count=asset.slide_count,
        slides=slides,
        pdf_url=asset.pdf_url,
        status=asset.status,
        linkedin_asset_urn=asset.linkedin_asset_urn,
        brand_kit=asset.brand_kit_snapshot,
        created_at=asset.created_at.isoformat() if asset.created_at else "",
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/{post_id}/carousel",
    status_code=status.HTTP_201_CREATED,
    response_model=CarouselAssetResponse,
    summary="Generate a 7-slide carousel from a post draft",
    description=(
        "Calls the AI Engine to generate a slide-by-slide outline, renders it as a "
        "branded PDF via the Carousel Renderer, and persists the CarouselAsset. "
        "The PDF URL is returned for in-browser preview."
    ),
)
async def generate_carousel(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CarouselService = Depends(get_carousel_service),
):
    logger.info("carousel_generate_called", post_id=str(post_id), user_id=str(current_user.id))
    try:
        asset = await service.create_carousel(post_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return _asset_to_response(asset)


@router.get(
    "/{post_id}/carousel",
    status_code=status.HTTP_200_OK,
    response_model=CarouselAssetResponse,
    summary="Get the most recent CarouselAsset for a post",
)
async def get_carousel(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CarouselService = Depends(get_carousel_service),
):
    asset = await service.get_by_post(post_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No carousel generated for this post yet. POST to /carousel to generate.",
        )
    return _asset_to_response(asset)


@router.post(
    "/{post_id}/carousel/publish",
    status_code=status.HTTP_200_OK,
    response_model=PublishCarouselResponse,
    summary="Publish carousel as a LinkedIn Document post",
    description=(
        "Executes LinkedIn's 3-step Document Upload API: "
        "(1) initializeUpload, (2) PUT PDF binary, (3) create post. "
        "Requires the user's LinkedIn OAuth access token."
    ),
)
async def publish_carousel(
    post_id: UUID,
    body: PublishCarouselRequest,
    current_user: User = Depends(get_current_user),
    service: CarouselService = Depends(get_carousel_service),
):
    # Get the most recent asset
    asset = await service.get_by_post(post_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No carousel found")

    # Decrypt LinkedIn access token
    if not current_user.access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn OAuth token not found — please re-authenticate",
        )
    try:
        access_token = decrypt_token(current_user.access_token_encrypted)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decrypt LinkedIn token — please re-authenticate",
        )

    try:
        li_post_urn = await service.publish_to_linkedin(
            asset_id=asset.id,
            user_id=current_user.id,
            access_token=access_token,
            post_text=body.post_text,
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("carousel_publish_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LinkedIn publish failed")

    return PublishCarouselResponse(
        linkedin_post_urn=li_post_urn,
        message="Carousel published successfully to LinkedIn ✅",
    )
