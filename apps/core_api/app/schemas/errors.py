"""
Structured application error codes and the AppError exception class.

Every API error that a frontend needs to handle programmatically should have
a corresponding code defined here. This lets the frontend branch on
`error.code` rather than parsing human-readable strings.

Response shape:
    {
        "code": "WRITE_TOKEN_EXPIRED",
        "detail": "LinkedIn write token has expired. Please re-connect your account.",
        "status_code": 401
    }
"""

from enum import Enum


class ErrorCode(str, Enum):
    # ── Authentication ───────────────────────────────────────────────────
    UNAUTHENTICATED = "UNAUTHENTICATED"                    # No/invalid JWT
    OAUTH_STATE_INVALID = "OAUTH_STATE_INVALID"            # CSRF state expired or tampered
    OAUTH_FAILED = "OAUTH_FAILED"                          # LinkedIn OAuth exchange failed

    # ── LinkedIn Write-Flow ──────────────────────────────────────────────
    WRITE_FLOW_NOT_CONNECTED = "WRITE_FLOW_NOT_CONNECTED"  # User never connected write account
    WRITE_TOKEN_EXPIRED = "WRITE_TOKEN_EXPIRED"            # Write token expired, needs re-auth
    WRITE_TOKEN_DECRYPT_FAILED = "WRITE_TOKEN_DECRYPT_FAILED"  # Fernet decryption failed

    # ── Carousel ─────────────────────────────────────────────────────────
    CAROUSEL_NOT_FOUND = "CAROUSEL_NOT_FOUND"              # No carousel for this post
    CAROUSEL_PDF_MISSING = "CAROUSEL_PDF_MISSING"          # Asset row exists but PDF file gone
    CAROUSEL_NOT_RENDERED = "CAROUSEL_NOT_RENDERED"        # Asset in draft state — not ready
    LINKEDIN_UPLOAD_FAILED = "LINKEDIN_UPLOAD_FAILED"      # LinkedIn document upload error
    LINKEDIN_POST_FAILED = "LINKEDIN_POST_FAILED"          # LinkedIn post creation error

    # ── Resources ────────────────────────────────────────────────────────
    NOT_FOUND = "NOT_FOUND"                                # Generic resource not found
    POST_NOT_FOUND = "POST_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # ── AI Engine ────────────────────────────────────────────────────────
    AI_ENGINE_UNAVAILABLE = "AI_ENGINE_UNAVAILABLE"        # Cannot reach AI engine
    AI_ENGINE_FAILED = "AI_ENGINE_FAILED"                  # AI engine returned an error

    # ── Validation ───────────────────────────────────────────────────────
    VALIDATION_ERROR = "VALIDATION_ERROR"                  # Request payload invalid

    # ── Storage ──────────────────────────────────────────────────────────
    PDF_STORAGE_FAILED = "PDF_STORAGE_FAILED"              # Could not write PDF to storage

    # ── General ──────────────────────────────────────────────────────────
    INTERNAL_ERROR = "INTERNAL_ERROR"                      # Unexpected server error
    RATE_LIMITED = "RATE_LIMITED"                          # Too many requests


class AppError(Exception):
    """
    Structured application exception.
    Raise this instead of bare ValueError/HTTPException when you want
    the frontend to receive a machine-readable error code.

    Example:
        raise AppError(
            code=ErrorCode.WRITE_TOKEN_EXPIRED,
            detail="LinkedIn write token has expired. Please re-connect your account.",
            status_code=401,
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        detail: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"AppError(code={self.code!r}, status={self.status_code}, detail={self.detail!r})"
