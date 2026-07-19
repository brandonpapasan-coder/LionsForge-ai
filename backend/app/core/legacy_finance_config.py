from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LegacyFinanceSettings(BaseSettings):
    enable_legacy_finance_modules: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_legacy_finance_settings() -> LegacyFinanceSettings:
    return LegacyFinanceSettings()
