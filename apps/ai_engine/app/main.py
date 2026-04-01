"""
AI Engine application factory.
Internal microservice — secured via API key, not exposed to public internet.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import structlog

from app.config import get_settings, get_yaml_config
from app.utils.logger import setup_logging

from app.controllers import health_controller, post_controller, comment_controller, idea_controller, classifier_controller, career_controller, sales_controller, talent_ai_controller, enterprise_ai_controller, evals_ai_controller, extraction_controller
from app.controllers import week_plan_controller

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        "app_starting",
        service="ai_engine",
        environment=settings.environment,
    )
    yield
    logger.info("app_shutting_down", service="ai_engine")


def create_app() -> FastAPI:
    """Create the AI Engine FastAPI application."""
    settings = get_settings()
    yaml_config = get_yaml_config()
    app_config = yaml_config.get("app", {})

    app = FastAPI(
        title=app_config.get("name", "LinkedIn-as-a-Service AI Engine"),
        version=app_config.get("version", "0.1.0"),
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # --- Routes ---
    app.include_router(health_controller.router)
    app.include_router(post_controller.router)
    app.include_router(comment_controller.router)
    app.include_router(idea_controller.router)
    app.include_router(classifier_controller.router)
    app.include_router(sales_controller.router)
    app.include_router(talent_ai_controller.router)
    app.include_router(enterprise_ai_controller.router)
    app.include_router(evals_ai_controller.router)
    app.include_router(extraction_controller.router)
    app.include_router(week_plan_controller.router)  # V2 — /webhooks/v2/generate/week-plan

    return app


# Uvicorn entry point
app = create_app()
