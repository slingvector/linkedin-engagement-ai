"""
Health check controller.
Exposes liveness and readiness probes per BACKEND_STANDARDS.md.
"""

from fastapi import APIRouter

from app.config import get_settings, get_yaml_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe — confirms the service is running."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "core_api",
        "environment": settings.environment,
    }


@router.get("/readiness")
async def readiness_check() -> dict:
    """Readiness probe — confirms the service can accept traffic."""
    yaml_config = get_yaml_config()
    return {
        "status": "ready",
        "service": "core_api",
        "version": yaml_config.get("app", {}).get("version", "unknown"),
    }
