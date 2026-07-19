from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LegacyMarketSettings(BaseSettings):
    market_data_provider: str = "mock"
    market_data_api_key: str | None = None
    market_data_failover_providers: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_legacy_market_settings() -> LegacyMarketSettings:
    return LegacyMarketSettings()
