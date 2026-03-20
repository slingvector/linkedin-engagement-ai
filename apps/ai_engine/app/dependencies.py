"""
AI Engine dependencies — API key verification for internal microservice security.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.config import get_settings

_api_key_header = APIKeyHeader(name="X-AI-API-Key", auto_error=True)


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    Verify the internal microservice API key.
    Only Core API (Dev 2's backend) should be able to call these webhooks.
    """
    settings = get_settings()
    if api_key != settings.ai_engine_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key
