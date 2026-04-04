"""
Core API configuration module.
Loads settings from environment variables and config.yaml.
All business-logic parameters are externalized — zero hardcoding.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Known insecure placeholder values that must not be used in production
_INSECURE_DEFAULTS = {
    "change_this_to_a_random_64_char_string",
    "change_this_internal_microservice_key",
    "generate_with_python_cryptography_fernet_generate_key",
    "",
}


def _load_yaml_config() -> dict:
    """Load config.yaml from the app root directory."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    YAML config is accessed separately via get_yaml_config().
    """

    # --- Environment ---
    environment: str = Field(default="development")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:changeme_local_only@localhost:5432/linkedin_saas"
    )

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- LinkedIn OAuth & Scraping ---
    linkedin_client_id: str = Field(default="")
    linkedin_client_secret: str = Field(default="")
    linkedin_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/linkedin/callback"
    )

    # --- Read Account (used by linkedin-read-flow / ingestion workers) ---
    linkedin_read_li_at_cookie: str = Field(default="")
    linkedin_read_email: str = Field(default="")
    linkedin_read_password: str = Field(default="")

    # --- Write Account (used by publish/reply workers) ---
    linkedin_write_li_at_cookie: str = Field(default="")
    linkedin_write_email: str = Field(default="")
    linkedin_write_password: str = Field(default="")

    # --- LinkedIn Write-Flow OAuth (V2 Carousel publish) ---
    linkedin_write_client_id: str = Field(default="")
    linkedin_write_client_secret: str = Field(default="")
    linkedin_write_redirect_uri: str = Field(
        default="http://localhost:8000/api/v2/auth/linkedin/callback"
    )

    # --- JWT ---
    jwt_secret_key: str = Field(default="change_this_to_a_random_64_char_string")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_minutes: int = Field(default=1440)

    # --- Encryption ---
    fernet_key: str = Field(default="")

    # --- AI Engine ---
    ai_engine_url: str = Field(default="http://localhost:8001")
    ai_engine_api_key: str = Field(default="change_this_internal_microservice_key")

    # --- Carousel Renderer ---
    carousel_renderer_url: str = Field(default="http://carousel_renderer:8002")

    # --- CORS ---
    # Comma-separated list of allowed origins.
    # Example: CORS_ALLOWED_ORIGINS=http://localhost:3000,https://myapp.example.com
    cors_allowed_origins: List[str] = Field(default=["http://localhost:3000"])

    # --- Observability ---
    log_level: str = Field(default="INFO")
    sentry_dsn: str = Field(default="")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def enforce_production_secrets(self) -> "Settings":
        """
        Fail loudly at startup if insecure placeholder secrets are used in production.
        In dev/staging, weak values are allowed (with a warning).
        """
        if self.environment == "production":
            insecure_fields = []
            if self.jwt_secret_key in _INSECURE_DEFAULTS:
                insecure_fields.append("JWT_SECRET_KEY")
            if self.fernet_key in _INSECURE_DEFAULTS:
                insecure_fields.append("FERNET_KEY")
            if self.ai_engine_api_key in _INSECURE_DEFAULTS:
                insecure_fields.append("AI_ENGINE_API_KEY")
            if insecure_fields:
                raise ValueError(
                    f"Production startup blocked — insecure placeholder values detected for: "
                    f"{', '.join(insecure_fields)}. Set real secrets in your .env file."
                )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()


@lru_cache
def get_yaml_config() -> dict:
    """Cached singleton for YAML business-logic config."""
    return _load_yaml_config()
