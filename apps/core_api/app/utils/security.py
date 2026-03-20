"""
Security utilities for JWT and token encryption.
"""

from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config import get_settings


def create_jwt_token(data: dict) -> str:
    """Create a JWT access token with expiry."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns None if invalid."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def encrypt_token(plain_text: str) -> str:
    """Encrypt a token (e.g., LinkedIn access token) using Fernet symmetric encryption."""
    settings = get_settings()
    if not settings.fernet_key:
        raise ValueError("FERNET_KEY is not configured")
    fernet = Fernet(settings.fernet_key.encode())
    return fernet.encrypt(plain_text.encode()).decode()


def decrypt_token(encrypted_text: str) -> str:
    """Decrypt a Fernet-encrypted token."""
    settings = get_settings()
    if not settings.fernet_key:
        raise ValueError("FERNET_KEY is not configured")
    fernet = Fernet(settings.fernet_key.encode())
    return fernet.decrypt(encrypted_text.encode()).decode()
