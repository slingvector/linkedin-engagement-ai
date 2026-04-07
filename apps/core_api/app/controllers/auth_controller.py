"""
Authentication controller — handles HTTP concerns for LinkedIn OAuth.
Controller layer: handles request/response only; delegates logic to AuthService.
"""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import get_settings, get_yaml_config
from app.dependencies import get_current_user, get_db, get_user_repository
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LinkedInAuthUrlResponse, TokenResponse
from app.services.auth_service import AuthService
from app.utils.oauth_state import consume_oauth_state, create_oauth_state

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/linkedin", response_model=LinkedInAuthUrlResponse)
async def linkedin_login(db: AsyncSession = Depends(get_db)) -> LinkedInAuthUrlResponse:
    """
    Generate the LinkedIn OAuth authorization URL.
    Frontend redirects the user to this URL to begin the OAuth flow.
    """
    settings = get_settings()
    yaml_config = get_yaml_config()
    auth_config = yaml_config.get("auth", {}).get("linkedin", {})

    # Generate and persist CSRF state token (Postgres-backed — survives restarts)
    state = await create_oauth_state(db, user_id=None)

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": " ".join(auth_config.get("scopes", ["openid", "profile", "email"])),
        "state": state,
    }
    auth_url = (
        f"{auth_config.get('auth_url', 'https://www.linkedin.com/oauth/v2/authorization')}"
        f"?{urlencode(params)}"
    )

    logger.info("oauth_initiated", state=state[:8] + "...")
    return LinkedInAuthUrlResponse(auth_url=auth_url)


@router.get("/linkedin/callback", response_model=TokenResponse)
async def linkedin_callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(..., description="CSRF state parameter"),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Handle the LinkedIn OAuth callback.
    Exchanges the code for tokens, upserts the user, returns a JWT.
    """
    # Validate and atomically consume CSRF state (prevents replay attacks)
    result = await consume_oauth_state(db, state)
    if result == "__invalid__":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please start the login flow again.",
        )

    try:
        service = AuthService(user_repository=user_repo)
        jwt_token = await service.authenticate_user(code)

        logger.info("oauth_complete", state=state[:8] + "...")
        return TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            expires_in_minutes=1440,
        )
    except Exception as e:
        logger.error("oauth_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again.",
        )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """
    Return the currently authenticated user's profile.
    Used by the frontend to validate the JWT on load and hydrate the UI.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture_url": current_user.profile_picture_url,
        "linkedin_id": current_user.linkedin_id,
        "subscription_tier": current_user.subscription_tier,
        "write_flow_connected": current_user.write_access_token_encrypted is not None,
    }
