"""
Global exception handler middleware.
Ensures consistent error responses per BACKEND_STANDARDS.md.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions. Log and return a clean 500."""
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Please try again.",
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError as a 400 Bad Request."""
        logger.warning(
            "value_error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": str(exc),
            },
        )
