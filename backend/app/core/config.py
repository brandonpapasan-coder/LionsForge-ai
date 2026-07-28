from datetime import datetime
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Onyxmane Intelligence"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    allow_mock_data: bool = True

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

    promotions_enabled: bool = False
    beta_lifetime_discount_enabled: bool = False
    founding_subscriber_enrollment_enabled: bool = False
    paid_beta_authorized: bool = False
    promotion_countdown_start_at: datetime | None = None
    promotion_countdown_launch_at: datetime | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def public_beta_promotion_enabled(self) -> bool:
        return (
            self.promotions_enabled
            and self.beta_lifetime_discount_enabled
            and self.paid_beta_authorized
        )

    def public_founding_promotion_enabled(self) -> bool:
        return (
            self.promotions_enabled
            and self.founding_subscriber_enrollment_enabled
            and self.paid_beta_authorized
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
