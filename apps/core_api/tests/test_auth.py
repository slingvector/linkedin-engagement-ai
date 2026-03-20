"""Tests for authentication utilities."""

import pytest

from app.utils.security import create_jwt_token, decode_jwt_token


class TestJWT:
    """JWT token creation and validation tests."""

    def test_create_and_decode_valid_token(self):
        """A created token should decode back to the original payload."""
        payload = {"sub": "test-user-id-123", "email": "test@example.com"}
        token = create_jwt_token(payload)
        decoded = decode_jwt_token(token)

        assert decoded is not None
        assert decoded["sub"] == payload["sub"]
        assert decoded["email"] == payload["email"]
        assert "exp" in decoded

    def test_decode_invalid_token_returns_none(self):
        """An invalid token should return None, not raise."""
        result = decode_jwt_token("this.is.garbage")
        assert result is None

    def test_decode_empty_token_returns_none(self):
        """An empty token should return None."""
        result = decode_jwt_token("")
        assert result is None
