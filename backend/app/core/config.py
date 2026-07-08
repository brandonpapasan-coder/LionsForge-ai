from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LionsForge AI"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    allow_mock_data: bool = True

    database_url: str = "sqlite:///./lionsforge.db"
    jwt_secret_key: str = "change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    market_data_provider: str = "mock"
    market_data_api_key: str | None = None
    news_provider: str = "mock"
    news_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
