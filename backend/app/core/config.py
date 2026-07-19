from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LionsForge AI"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    allow_mock_data: bool = True
    enable_legacy_finance_modules: bool = False

    database_url: str = "sqlite:///./lionsforge.db"
    jwt_secret_key: str = "change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    redis_url: str | None = None
    news_provider: str = "mock"
    news_api_key: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
