"""
config.py — Application settings loaded from environment / .env file.
All modules import settings from here; never read os.environ directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "IncuBrix Economics Engine"
    app_version: str = "1.0.0"
    debug: bool = True
    feature_flag_economics_engine: bool = True

    # Database
    database_url: str = "sqlite:///./economics_engine.db"

    # API
    api_prefix: str = "/api/video-economics"
    port: int = 8000

    # Policy defaults
    default_async_savings_threshold: float = 0.15
    default_near_budget_threshold: float = 0.85
    default_uncertainty_low_multiplier: float = 0.9
    default_uncertainty_high_multiplier: float = 1.2


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
