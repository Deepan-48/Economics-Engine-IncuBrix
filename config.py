from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "IncuBrix Economics Engine v2"
    app_version: str = "2.0.0"
    debug: bool = True
    database_url: str = "sqlite:///./economics_engine_v2.db"
    api_prefix: str = "/api/video-economics"
    port: int = 8000
    default_async_savings_threshold: float = 0.15
    default_near_budget_threshold: float = 0.85
    default_uncertainty_low_multiplier: float = 0.9
    default_uncertainty_high_multiplier: float = 1.2

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
