"""
V2 Auth Controller — LinkedIn Write-Flow OAuth
==============================================
Provides a separate OAuth flow for the write-flow LinkedIn app that has
w_member_social scope (required for posting documents/carousels).

Flow:
  1. GET  /api/v2/auth/linkedin        → redirect user to LinkedIn consent
  2. GET  /api/v2/auth/linkedin/callback → exchange code → store write token on user
"""

from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.utils.oauth_state import consume_oauth_state, create_oauth_state
from app.utils.security import encrypt_token

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["v2-auth"])


def _get_redirect_uri(request: Request, settings) -> str:
    """
    Resolves the redirect URI dynamically.
    If the request comes through a Cloudflare tunnel, we use the tunnel's hostname
    to ensure LinkedIn's redirect returns the user to the correct origin.
    """
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    if "trycloudflare.com" in host:
        return f"https://{host}/api/v2/auth/linkedin/callback"
    return settings.linkedin_write_redirect_uri


@router.get("/linkedin", summary="Start LinkedIn write-flow OAuth consent")
async def write_flow_login(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generates the LinkedIn OAuth authorization URL for write-flow consent.
    The user must be logged in (read-flow JWT) to initiate.
    Returns a URL the frontend should redirect to.
    """
    settings = get_settings()

    # Persist state with user_id — so callback knows who to update
    state = await create_oauth_state(db, user_id=str(current_user.id))

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_write_client_id,
        "redirect_uri": _get_redirect_uri(request, settings),
        "scope": "w_member_social openid profile email",
        "state": state,
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    logger.info("write_flow_oauth_initiated", user_id=str(current_user.id), state=state[:8])
    return {"auth_url": auth_url}


@router.get("/linkedin/callback", summary="Handle LinkedIn write-flow OAuth callback")
async def write_flow_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(..., description="CSRF state parameter"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Exchanges the authorization code for a write-flow access token.
    Encrypts and stores the token on the User record so CarouselService
    can use it for Document Upload + post creation.
    """
    # 1. Validate and consume CSRF state (Postgres-backed — restart/multi-worker safe)
    user_id = await consume_oauth_state(db, state)
    if user_id == "__invalid__":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the flow again.",
        )

    settings = get_settings()

    # 2. Exchange code for access token
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            redirect_uri = _get_redirect_uri(request, settings)
            token_resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": settings.linkedin_write_client_id,
                    "client_secret": settings.linkedin_write_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_resp.status_code != 200:
                logger.error(
                    "linkedin_token_exchange_error",
                    status=token_resp.status_code,
                    body=token_resp.text,
                )
            token_resp.raise_for_status()
            token_data = token_resp.json()
    except Exception as e:
        logger.error("write_flow_token_exchange_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn token exchange failed: {e}",
        )

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access_token in LinkedIn response",
        )

    # 3. Fetch LinkedIn person ID via userinfo
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            profile_resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()
    except Exception as e:
        logger.warning("write_flow_userinfo_failed", error=str(e))
        profile = {}

    linkedin_person_id = profile.get("sub", "")

    # 4. Persist encrypted write token + person ID on user record
    from sqlalchemy import select as sa_select
    result = await db.execute(sa_select(User).where(User.id == user_id))  # type: ignore[arg-type]
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.write_access_token_encrypted = encrypt_token(access_token)
    if linkedin_person_id:
        user.linkedin_person_id = linkedin_person_id
    await db.commit()

    logger.info(
        "write_flow_oauth_complete",
        user_id=user_id,
        linkedin_person_id=linkedin_person_id,
    )
    return {
        "message": "LinkedIn write-flow connected successfully",
        "linkedin_person_id": linkedin_person_id,
        "scopes_granted": token_data.get("scope", ""),
    }
