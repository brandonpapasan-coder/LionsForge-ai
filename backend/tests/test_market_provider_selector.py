import pytest

from app.core.config import get_settings
from app.services.provider_selector import (
    MarketProviderConfigurationError,
    get_configured_market_provider,
)


def test_mock_provider_selected_by_default():
    get_settings.cache_clear()
    provider = get_configured_market_provider()
    assert provider.name == "mock-market-data"


def test_unsupported_provider_raises(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "unsupported")
    get_settings.cache_clear()
    with pytest.raises(MarketProviderConfigurationError):
        get_configured_market_provider()
    monkeypatch.delenv("MARKET_DATA_PROVIDER")
    get_settings.cache_clear()
