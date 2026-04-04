"""
Core API configuration module.
Loads settings from environment variables and config.yaml.
All business-logic parameters are externalized — zero hardcoding.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings
from pydantic import Field


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

    # --- Carousel Renderer (Sprint 4 microservice) ---
    carousel_renderer_url: str = Field(default="http://carousel_renderer:8002")

    # --- Observability ---
    log_level: str = Field(default="INFO")
    sentry_dsn: str = Field(default="")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()


@lru_cache
def get_yaml_config() -> dict:
    """Cached singleton for YAML business-logic config."""
    return _load_yaml_config()
