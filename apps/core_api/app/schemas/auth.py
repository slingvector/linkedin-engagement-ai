"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field


class LinkedInAuthUrlResponse(BaseModel):
    """Response containing the LinkedIn OAuth authorization URL."""
    auth_url: str = Field(..., description="URL to redirect the user to for LinkedIn login")


class LinkedInCallbackRequest(BaseModel):
    """Query params received from LinkedIn OAuth callback."""
    code: str = Field(..., description="Authorization code from LinkedIn")
    state: str = Field(..., description="CSRF state parameter")


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class AuthStatusResponse(BaseModel):
    """Current auth status for the logged-in user."""
    is_authenticated: bool
    user_id: str | None = None
    email: str | None = None
