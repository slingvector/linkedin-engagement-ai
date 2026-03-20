"""
Authentication service — business logic layer.
Handles LinkedIn OAuth flow and JWT token management.
"""

import secrets
from urllib.parse import urlencode

import httpx
import structlog

from app.config import get_settings, get_yaml_config
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import create_jwt_token, encrypt_token

logger = structlog.get_logger()


class AuthService:
    """
    Orchestrates the LinkedIn OAuth 2.0 flow.

    Separation of concerns:
    - This service handles business logic (token exchange, user upsert).
    - The repository handles data access.
    - The controller handles HTTP concerns.
    """

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()

    def generate_auth_url(self) -> tuple[str, str]:
        """
        Build the LinkedIn OAuth authorization URL.
        Returns (auth_url, state_token) for CSRF protection.
        """
        state = secrets.token_urlsafe(32)
        auth_config = self._yaml_config.get("auth", {}).get("linkedin", {})

        params = {
            "response_type": "code",
            "client_id": self._settings.linkedin_client_id,
            "redirect_uri": self._settings.linkedin_redirect_uri,
            "scope": " ".join(auth_config.get("scopes", ["openid", "profile", "email"])),
            "state": state,
        }

        auth_url = f"{auth_config.get('auth_url', 'https://www.linkedin.com/oauth/v2/authorization')}?{urlencode(params)}"
        return auth_url, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchange the authorization code for LinkedIn access/refresh tokens.
        """
        auth_config = self._yaml_config.get("auth", {}).get("linkedin", {})
        token_url = auth_config.get("token_url", "https://www.linkedin.com/oauth/v2/accessToken")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
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

    async def authenticate_user(self, code: str) -> str:
        """
        Full OAuth flow: exchange code → fetch profile → upsert user → return JWT.

        Returns a JWT access token for the frontend.
        """
        # 1. Exchange authorization code for tokens
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data["access_token"]

        # 2. Fetch user profile from LinkedIn
        profile = await self.fetch_user_profile(access_token)

        linkedin_id = profile.get("sub", "")
        email = profile.get("email", "")
        full_name = profile.get("name", "")
        picture = profile.get("picture", "")

        # 3. Upsert user in database
        user = await self._user_repo.get_by_linkedin_id(linkedin_id)

        if user:
            # Update existing user tokens
            user.access_token_encrypted = encrypt_token(access_token)
            user.email = email
            user.full_name = full_name
            user.profile_picture_url = picture
            await self._user_repo.update(user)
            logger.info("user_login", user_id=str(user.id), action="returning_user")
        else:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                linkedin_id=linkedin_id,
                profile_picture_url=picture,
                access_token_encrypted=encrypt_token(access_token),
            )
            user = await self._user_repo.create(user)
            logger.info("user_login", user_id=str(user.id), action="new_user")

        # 4. Generate JWT for frontend
        jwt_token = create_jwt_token({"sub": str(user.id), "email": user.email})
        return jwt_token
