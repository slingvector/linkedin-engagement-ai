"""
Authentication controller — handles HTTP concerns for LinkedIn OAuth.
Controller layer: handles request/response only; delegates logic to AuthService.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.dependencies import get_user_repository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LinkedInAuthUrlResponse, TokenResponse
from app.services.auth_service import AuthService

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory state store for CSRF protection (use Redis in production)
_oauth_states: dict[str, bool] = {}


@router.get("/linkedin", response_model=LinkedInAuthUrlResponse)
async def linkedin_login() -> LinkedInAuthUrlResponse:
    """
    Generate the LinkedIn OAuth authorization URL.
    Frontend redirects the user to this URL.
    """
    service = AuthService(user_repository=None)  # No DB needed for URL generation
    auth_url, state = service.generate_auth_url()

    # Store state for CSRF validation
    _oauth_states[state] = True

    logger.info("oauth_initiated", state=state[:8] + "...")
    return LinkedInAuthUrlResponse(auth_url=auth_url)


@router.get("/linkedin/callback", response_model=TokenResponse)
async def linkedin_callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    state: str = Query(..., description="CSRF state parameter"),
    user_repo: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """
    Handle the LinkedIn OAuth callback.
    Exchanges the code for tokens, upserts the user, returns a JWT.
    """
    # Validate CSRF state
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    del _oauth_states[state]

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
