"""
CarouselService — Core API V2, Sprint 4
=========================================
Orchestrates the full carousel creation pipeline:

  1. Load the originating Post (validates user ownership)
  2. Fetch user's brand kit from UserSettings (or use defaults)
  3. Call AI Engine → POST /webhooks/v2/generate/carousel-outline
  4. Call Carousel Renderer → POST /render  (returns PDF bytes)
  5. Persist PDF to local storage (dev) or GCS (prod) → get URL
  6. Persist CarouselAsset to DB  (status: rendered)
  7. Return the CarouselAsset

LinkedIn Document Upload (called separately on user-triggered publish):
  Step 1: POST /rest/documents?action=initializeUpload  → uploadUrl + document URN
  Step 2: PUT {uploadUrl} with PDF binary
  Step 3: POST /rest/posts with {content: {media: {id: "urn:li:document:..."}}}
"""

import base64
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.carousel import CarouselAsset
from app.models.post import Post
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.post_repository import PostRepository
from app.schemas.errors import AppError, ErrorCode
from app.utils.security import decrypt_token

logger = structlog.get_logger()

# Local PDF storage (dev) — swapped for GCS in prod
_PDF_STORE = Path("/tmp/carousel_pdfs")
_PDF_STORE.mkdir(parents=True, exist_ok=True)


class CarouselService:

    def __init__(self, post_repo: PostRepository, db: AsyncSession):
        self._repo = post_repo
        self._db = db
        self._settings = get_settings()

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_carousel(self, post_id: UUID, user_id: UUID) -> CarouselAsset:
        """
        Full pipeline: outline → render → persist.
        Returns the saved CarouselAsset.
        """
        # 1. Load post
        post = await self._repo.get_by_id(post_id, user_id)
        if not post:
            raise ValueError(f"Post {post_id} not found for user {user_id}")

        # 2. Fetch brand kit
        brand_kit = await self._get_brand_kit(user_id)

        # 3. Call AI Engine for slide outline
        outline = await self._call_ai_engine_outline(post, user_id)
        if not outline:
            raise RuntimeError("AI Engine failed to generate carousel outline")

        slides_json = outline.get("slides", [])
        cover_hook = outline.get("cover_hook", post.hook)
        cta_text = outline.get("cta_slide_text", "Follow for more")

        # 4. Render PDF
        pdf_bytes = await self._render_pdf(slides_json, brand_kit, cover_hook, cta_text)

        # 5. Persist PDF (local dev / GCS prod)
        pdf_url = await self._store_pdf(pdf_bytes, post_id)

        # 6. Persist CarouselAsset
        asset = CarouselAsset(
            post_id=post_id,
            slides_json=slides_json,
            pdf_url=pdf_url,
            slide_count=len(slides_json),
            status="rendered" if pdf_url else "draft",
            brand_kit_snapshot=brand_kit,
        )
        self._db.add(asset)
        await self._db.commit()
        await self._db.refresh(asset)

        logger.info(
            "carousel_created",
            post_id=str(post_id),
            asset_id=str(asset.id),
            slides=len(slides_json),
            pdf_url=pdf_url,
        )

        return asset

    async def get_by_post(self, post_id: UUID) -> CarouselAsset | None:
        """Return the most recent CarouselAsset for a post."""
        result = await self._db.execute(
            select(CarouselAsset)
            .where(
                CarouselAsset.post_id == post_id,
                CarouselAsset.deleted_at.is_(None),
            )
            .order_by(CarouselAsset.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def publish_to_linkedin(
        self,
        asset_id: UUID,
        user_id: UUID,
        post_text: str,
    ) -> str:
        """
        LinkedIn 3-step Document Upload.
        Reads the write-flow access token from the User record.
        Returns the LinkedIn post URN on success.
        """
        # Load asset
        result = await self._db.execute(
            select(CarouselAsset).where(CarouselAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if not asset or not asset.pdf_url:
            raise ValueError("CarouselAsset not found or PDF not rendered")

        # Read PDF bytes
        pdf_path = Path(asset.pdf_url.replace("file://", ""))
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
        pdf_bytes = pdf_path.read_bytes()

        # Load user to get write-flow token (with transparent refresh)
        user_result = await self._db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise AppError(
                code=ErrorCode.USER_NOT_FOUND,
                detail=f"User {user_id} not found.",
                status_code=404,
            )
        if not user.write_access_token_encrypted:
            raise AppError(
                code=ErrorCode.WRITE_FLOW_NOT_CONNECTED,
                detail="LinkedIn write account not connected. Please authorize in Settings.",
                status_code=400,
            )

        # Attempt to get a valid (possibly refreshed) write-flow token
        try:
            from app.services.auth_service import AuthService
            from app.repositories.user_repository import UserRepository
            user_repo = UserRepository(self._db)
            auth_service = AuthService(user_repository=user_repo)

            # Use write-flow token directly since it has separate expiry tracking
            # For write tokens we fall back to direct decrypt (refresh_token for write-flow
            # is managed by the v2/auth flow separately)
            if auth_service.is_token_expiring_soon(user) and user.refresh_token_encrypted:
                access_token = await auth_service.refresh_linkedin_token(user)
            else:
                access_token = decrypt_token(user.write_access_token_encrypted)
        except AppError:
            raise
        except Exception as e:
            raise AppError(
                code=ErrorCode.WRITE_TOKEN_DECRYPT_FAILED,
                detail="Could not decrypt LinkedIn write token. Please re-connect your account.",
                status_code=400,
            )
        person_id = user.linkedin_person_id or user.linkedin_id  # fall back to slug
        person_urn = f"urn:li:person:{person_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202603",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Initialize upload
            init_resp = await client.post(
                "https://api.linkedin.com/rest/documents",
                params={"action": "initializeUpload"},
                json={
                    "initializeUploadRequest": {
                        "owner": person_urn,
                    }
                },
                headers=headers,
            )
            if init_resp.status_code != 200:
                logger.error("linkedin_init_upload_failed",
                             status=init_resp.status_code,
                             body=init_resp.text)
                if init_resp.status_code == 401:
                    raise ValueError("LinkedIn write token expired. Please re-authorize.")
                init_resp.raise_for_status()

            init_data = init_resp.json().get("value", {})
            upload_url = init_data.get("uploadUrl")
            document_urn = init_data.get("document")

            if not upload_url or not document_urn:
                raise RuntimeError("LinkedIn upload initialization failed — no uploadUrl returned")

            logger.info("carousel_upload_initialized", document_urn=document_urn, person_urn=person_urn)

            # Step 2: Upload PDF binary
            put_resp = await client.put(
                upload_url,
                content=pdf_bytes,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream",
                },
            )
            if put_resp.status_code not in (200, 201):
                logger.error("linkedin_pdf_upload_failed", status=put_resp.status_code, body=put_resp.text)
                put_resp.raise_for_status()

            # Step 3: Create the LinkedIn post
            post_resp = await client.post(
                "https://api.linkedin.com/rest/posts",
                json={
                    "author": person_urn,
                    "commentary": post_text,
                    "visibility": "PUBLIC",
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "content": {
                        "media": {
                            "id": document_urn,
                            "title": post_text[:100],
                        }
                    },
                    "lifecycleState": "PUBLISHED",
                    "isReshareDisabledByAuthor": False,
                },
                headers=headers,
            )
            if post_resp.status_code != 201:
                logger.error("linkedin_post_creation_failed",
                             status=post_resp.status_code,
                             body=post_resp.text)
                if post_resp.status_code == 401:
                    raise ValueError("LinkedIn post creation refused — re-authorize to grant w_member_social scope.")
                post_resp.raise_for_status()

            li_post_urn = post_resp.headers.get("x-restli-id", "")

        # Update asset with LinkedIn URN
        asset.linkedin_asset_urn = document_urn
        asset.status = "published"
        await self._db.commit()

        logger.info(
            "carousel_published_linkedin",
            asset_id=str(asset_id),
            document_urn=document_urn,
            li_post_urn=li_post_urn,
        )

        return li_post_urn

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_brand_kit(self, user_id: UUID) -> dict:
        """Fetch user brand kit or return defaults."""
        result = await self._db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            return {
                "primary_color": settings.primary_color or "#0A66C2",
                "logo_url": settings.logo_url,
                "font_family": settings.font_family or "Inter",
                "author_name": settings.author_name or "",
                "author_tagline": settings.author_tagline or "",
            }
        return {
            "primary_color": "#0A66C2",
            "logo_url": None,
            "font_family": "Inter",
            "author_name": "",
            "author_tagline": "",
        }

    async def _call_ai_engine_outline(self, post: Post, user_id: UUID) -> dict | None:
        """Call AI Engine to generate 7-slide outline."""
        url = f"{self._settings.ai_engine_url}/webhooks/v2/generate/carousel-outline"
        headers = {"X-AI-API-Key": self._settings.ai_engine_api_key}
        payload = {
            "user_id": str(user_id),
            "topic": f"{post.topic}: {post.hook}",
            "audience": post.audience,
            "tone": post.tone or "professional_but_conversational",
            "slide_count": 7,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("carousel_outline_engine_failed", error=str(e))
            return None

    async def _render_pdf(
        self,
        slides: list[dict],
        brand_kit: dict,
        cover_hook: str,
        cta_text: str,
    ) -> bytes | None:
        """
        Call the Carousel Renderer microservice.
        Falls back to None if renderer is not available (dev without renderer running).
        """
        renderer_url = getattr(self._settings, "carousel_renderer_url", "http://localhost:8002")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{renderer_url}/render",
                    json={
                        "slides": slides,
                        "brand_kit": brand_kit,
                        "cover_hook": cover_hook,
                        "cta_text": cta_text,
                    },
                )
                resp.raise_for_status()
                # Renderer returns: {"pdf_base64": "..."}
                data = resp.json()
                return base64.b64decode(data["pdf_base64"])
        except Exception as e:
            logger.warning("carousel_renderer_unavailable", error=str(e))
            return None

    async def _store_pdf(self, pdf_bytes: bytes | None, post_id: UUID) -> str | None:
        """Store PDF locally (dev). In prod, upload to GCS and return signed URL."""
        if not pdf_bytes:
            return None
        filename = f"{post_id}.pdf"
        dest = _PDF_STORE / filename
        dest.write_bytes(pdf_bytes)
        pdf_url = f"file://{dest}"
        logger.info("carousel_pdf_stored", path=str(dest))
        return pdf_url
