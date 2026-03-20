"""
Health check controller for AI Engine.
"""

from fastapi import APIRouter

from app.config import get_settings, get_yaml_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "ai_engine",
        "environment": settings.environment,
    }


@router.get("/readiness")
async def readiness_check() -> dict:
    """Readiness probe."""
    yaml_config = get_yaml_config()
    settings = get_settings()
    return {
        "status": "ready",
        "service": "ai_engine",
        "version": yaml_config.get("app", {}).get("version", "unknown"),
        "llm_model": yaml_config.get("llm", {}).get("models", {}).get(
            settings.environment, "unknown"
        ),
    }
