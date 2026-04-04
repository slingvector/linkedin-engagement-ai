"""
Authentication service — business logic layer.
Handles LinkedIn OAuth flow, token storage, token refresh, and JWT management.
"""

from datetime import datetime, timezone, timedelta

import httpx
import structlog

from app.config import get_settings, get_yaml_config
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.errors import AppError, ErrorCode
from app.utils.security import create_jwt_token, encrypt_token, decrypt_token

logger = structlog.get_logger()

# LinkedIn access tokens are valid for 60 days; refresh tokens for 365 days.
# We refresh proactively when less than TOKEN_REFRESH_BUFFER_MINUTES remain.
TOKEN_REFRESH_BUFFER_MINUTES = 10


class AuthService:
    """
    Orchestrates the LinkedIn OAuth 2.0 flow, token refresh, and user management.

    Separation of concerns:
    - This service handles business logic (token exchange, refresh, user upsert).
    - The repository handles data access.
    - The controller handles HTTP concerns.
    """

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()

    def _token_url(self) -> str:
        auth_config = self._yaml_config.get("auth", {}).get("linkedin", {})
        return auth_config.get("token_url", "https://www.linkedin.com/oauth/v2/accessToken")

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchange the authorization code for LinkedIn access/refresh tokens.
        Returns the full token response dict from LinkedIn.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._token_url(),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._settings.linkedin_redirect_uri,
                    "client_id": self._settings.linkedin_client_id,
                    "client_secret": self._settings.linkedin_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_user_profile(self, access_token: str) -> dict:
        """Fetch the user's profile from LinkedIn's userinfo endpoint."""
        auth_config = self._yaml_config.get("auth", {}).get("linkedin", {})
        userinfo_url = auth_config.get("userinfo_url", "https://api.linkedin.com/v2/userinfo")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_linkedin_token(self, user: User) -> str:
        """
        Use the stored refresh token to obtain a new LinkedIn access token.

        Updates the user record in-place with the new token and expiry.
        Returns the plaintext new access token.

        Raises AppError(WRITE_TOKEN_EXPIRED) if no refresh token is available
        or if LinkedIn rejects the refresh — user must re-authorize from scratch.
        """
        if not user.refresh_token_encrypted:
            raise AppError(
                code=ErrorCode.WRITE_TOKEN_EXPIRED,
                detail="LinkedIn session expired and no refresh token is available. Please sign in again.",
                status_code=401,
            )

        try:
            refresh_token = decrypt_token(user.refresh_token_encrypted)
        except Exception:
            raise AppError(
                code=ErrorCode.WRITE_TOKEN_DECRYPT_FAILED,
                detail="Could not decrypt refresh token. Please sign in again.",
                status_code=401,
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url(),
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._settings.linkedin_client_id,
                        "client_secret": self._settings.linkedin_client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if response.status_code in (400, 401):
                    # Refresh token revoked or expired — user must re-authenticate
                    raise AppError(
                        code=ErrorCode.WRITE_TOKEN_EXPIRED,
                        detail="LinkedIn session has fully expired. Please sign in again.",
                        status_code=401,
                    )
                response.raise_for_status()
                token_data = response.json()
        except AppError:
            raise
        except Exception as e:
            logger.error("token_refresh_failed", error=str(e), user_id=str(user.id))
            raise AppError(
                code=ErrorCode.WRITE_TOKEN_EXPIRED,
                detail="Failed to refresh LinkedIn token. Please sign in again.",
                status_code=401,
            )

        new_access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 5184000)  # LinkedIn default: 60 days

        # Persist refreshed tokens
        user.access_token_encrypted = encrypt_token(new_access_token)
        user.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        if "refresh_token" in token_data:
            user.refresh_token_encrypted = encrypt_token(token_data["refresh_token"])

        await self._user_repo.update(user)
        logger.info("token_refreshed", user_id=str(user.id), expires_in=expires_in)
        return new_access_token

    def is_token_expiring_soon(self, user: User) -> bool:
        """
        Returns True if the user's access token will expire within the buffer window,
        or if no expiry is stored (treat as expired so we attempt a refresh).
        """
        if not user.token_expires_at:
            return True  # No stored expiry — assume we should refresh
        threshold = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
        expires_at = user.token_expires_at
        # Normalise to aware datetime if stored as naive
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= threshold

    async def get_valid_access_token(self, user: User) -> str:
        """
        Returns a valid plaintext access token for `user`, refreshing transparently
        if it's expiring soon. Raises AppError if refresh is not possible.
        """
        if self.is_token_expiring_soon(user):
            logger.info("token_proactive_refresh", user_id=str(user.id))
            return await self.refresh_linkedin_token(user)

        if not user.access_token_encrypted:
            raise AppError(
                code=ErrorCode.WRITE_FLOW_NOT_CONNECTED,
                detail="LinkedIn account not connected. Please sign in.",
                status_code=401,
            )

        try:
            return decrypt_token(user.access_token_encrypted)
        except Exception:
            raise AppError(
                code=ErrorCode.WRITE_TOKEN_DECRYPT_FAILED,
                detail="Could not decrypt access token. Please sign in again.",
                status_code=401,
            )

    async def authenticate_user(self, code: str) -> str:
        """
        Full OAuth flow: exchange code → fetch profile → upsert user → return JWT.
        Stores both access_token and refresh_token encrypted, plus token_expires_at.
        Returns a JWT access token for the frontend.
        """
        # 1. Exchange authorization code for tokens
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 5184000)  # 60 days in seconds

        # 2. Fetch user profile from LinkedIn
        profile = await self.fetch_user_profile(access_token)

        linkedin_id = profile.get("sub", "")
        email = profile.get("email", "")
        full_name = profile.get("name", "")
        picture = profile.get("picture", "")
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # 3. Upsert user in database
        user = await self._user_repo.get_by_linkedin_id(linkedin_id)

        if user:
            user.access_token_encrypted = encrypt_token(access_token)
            user.token_expires_at = token_expires_at
            if refresh_token:
                user.refresh_token_encrypted = encrypt_token(refresh_token)
            user.email = email
            user.full_name = full_name
            user.profile_picture_url = picture
            await self._user_repo.update(user)
            logger.info("user_login", user_id=str(user.id), action="returning_user")
        else:
            user = User(
                email=email,
                full_name=full_name,
                linkedin_id=linkedin_id,
                profile_picture_url=picture,
                access_token_encrypted=encrypt_token(access_token),
                token_expires_at=token_expires_at,
                refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            )
            user = await self._user_repo.create(user)
            logger.info("user_login", user_id=str(user.id), action="new_user")

        # 4. Generate JWT for frontend
        jwt_token = create_jwt_token({"sub": str(user.id), "email": user.email})
        return jwt_token
