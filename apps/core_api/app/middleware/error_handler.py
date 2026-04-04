"""
Global exception handler middleware.
Emits structured error responses: { "code": "...", "detail": "..." }
so the frontend can branch on machine-readable codes, not strings.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

from app.schemas.errors import AppError, ErrorCode

logger = structlog.get_logger()


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Handle structured AppErrors — pass the code through directly."""
        logger.warning(
            "app_error",
            code=exc.code,
            detail=exc.detail,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """
        Handle bare ValueErrors from service layer.
        Map known sentinel strings to structured error codes.
        """
        detail = str(exc)
        code = _classify_value_error(detail)

        logger.warning(
            "value_error",
            code=code,
            detail=detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=400,
            content={
                "code": code,
                "detail": detail,
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        """PDF file missing from storage — asset needs to be re-rendered."""
        logger.warning(
            "file_not_found",
            code=ErrorCode.CAROUSEL_PDF_MISSING,
            detail=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=404,
            content={
                "code": ErrorCode.CAROUSEL_PDF_MISSING,
                "detail": "The carousel PDF is missing from storage. Please re-generate the carousel.",
            },
        )

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
                "code": ErrorCode.INTERNAL_ERROR,
                "detail": "An unexpected error occurred. Please try again.",
            },
        )


def _classify_value_error(detail: str) -> str:
    """
    Map known service-layer ValueError message sentinels to structured error codes.
    Keeps service layer free of HTTP concepts while giving the frontend usable codes.
    """
    lower = detail.lower()
    if "write_flow_not_connected" in lower or "write_access_token" in lower:
        return ErrorCode.WRITE_FLOW_NOT_CONNECTED
    if "write token expired" in lower or "re-authorize" in lower:
        return ErrorCode.WRITE_TOKEN_EXPIRED
    if "decryption failed" in lower or "decrypt" in lower:
        return ErrorCode.WRITE_TOKEN_DECRYPT_FAILED
    if "pdf not rendered" in lower or "not rendered" in lower:
        return ErrorCode.CAROUSEL_NOT_RENDERED
    if "pdf not found" in lower or "carousel" in lower and "not found" in lower:
        return ErrorCode.CAROUSEL_NOT_FOUND
    if "post" in lower and "not found" in lower:
        return ErrorCode.POST_NOT_FOUND
    if "ai engine failed" in lower:
        return ErrorCode.AI_ENGINE_FAILED
    if "upload initialization failed" in lower:
        return ErrorCode.LINKEDIN_UPLOAD_FAILED
    return ErrorCode.VALIDATION_ERROR
