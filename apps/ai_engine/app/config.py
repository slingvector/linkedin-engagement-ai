"""
AI Engine configuration module.
Loads settings from environment variables and config.yaml.
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
    """AI Engine settings from environment variables."""

    # --- Environment ---
    environment: str = Field(default="development")

    # --- Security ---
    ai_engine_api_key: str = Field(default="change_this_internal_microservice_key")

    # --- LLM ---
    openai_api_key: str = Field(default="")

    # --- Observability ---
    log_level: str = Field(default="INFO")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()


@lru_cache
def get_yaml_config() -> dict:
    """Cached singleton for YAML config."""
    return _load_yaml_config()
