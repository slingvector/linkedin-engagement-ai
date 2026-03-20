"""
Core API application factory.
Creates and configures the FastAPI app with all routes, middleware, and lifespan events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings, get_yaml_config
from app.middleware.error_handler import register_error_handlers
from app.controllers import auth_controller, health_controller, post_controller, creator_controller, idea_controller, analytics_controller, career_controller, sales_controller, talent_controller, enterprise_controller, llmops_controller
from app.utils.logger import setup_logging
from app.workers.ingestion_worker import safe_ingest_mock_posts
from app.workers.publishing_worker import publishing_scheduler_loop
from app.workers.metrics_worker import poll_metrics_and_classifications
from app.workers.job_seeder import sync_remote_job_board
from app.workers.lead_seeder import seed_leads_loop
from app.workers.candidate_seeder import seed_candidates_loop
from app.workers.signal_seeder import seed_enterprise_signals_loop
from app.workers.evals_worker import seed_evals_loop
import asyncio

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        "app_starting",
        service="core_api",
        environment=settings.environment,
    )
    
    # Start background workers
    ingestion_task = asyncio.create_task(safe_ingest_mock_posts())
    publishing_task = asyncio.create_task(publishing_scheduler_loop())
    metrics_task = asyncio.create_task(poll_metrics_and_classifications())
    job_seeder_task = asyncio.create_task(sync_remote_job_board())
    lead_seeder_task = asyncio.create_task(seed_leads_loop())
    candidate_seeder_task = asyncio.create_task(seed_candidates_loop())
    signal_seeder_task = asyncio.create_task(seed_enterprise_signals_loop())
    evals_task = asyncio.create_task(seed_evals_loop())

    yield
    
    # Shutdown: Clean up connections
    ingestion_task.cancel()
    publishing_task.cancel()
    metrics_task.cancel()
    job_seeder_task.cancel()
    lead_seeder_task.cancel()
    candidate_seeder_task.cancel()
    signal_seeder_task.cancel()
    evals_task.cancel()
    logger.info("app_shutting_down", service="core_api")


def create_app() -> FastAPI:
    """
    Application factory pattern.
    Creates a fully configured FastAPI instance.
    """
    settings = get_settings()
    yaml_config = get_yaml_config()
    app_config = yaml_config.get("app", {})

    app = FastAPI(
        title=app_config.get("name", "LinkedIn-as-a-Service Core API"),
        version=app_config.get("version", "0.1.0"),
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Next.js dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Error Handlers ---
    register_error_handlers(app)

    # --- Routes ---
    api_prefix = app_config.get("api_prefix", "/api/v1")
    app.include_router(health_controller.router)
    app.include_router(auth_controller.router, prefix=api_prefix)
    app.include_router(post_controller.router, prefix=api_prefix)
    app.include_router(creator_controller.radar_router, prefix=api_prefix)
    app.include_router(creator_controller.copilot_router, prefix=api_prefix)
    app.include_router(idea_controller.router, prefix=api_prefix)
    app.include_router(analytics_controller.router)
    app.include_router(career_controller.router)
    app.include_router(sales_controller.router, prefix=api_prefix)
    app.include_router(talent_controller.router, prefix=api_prefix)
    app.include_router(enterprise_controller.router, prefix=api_prefix)
    app.include_router(llmops_controller.router, prefix=api_prefix)

    return app


# Uvicorn entry point
app = create_app()
