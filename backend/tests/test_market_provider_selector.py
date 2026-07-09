import pytest

from app.core.config import get_settings
from app.services.market_providers import LiveMarketDataProvider
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


def test_live_provider_requires_api_key(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "alpaca")
    monkeypatch.delenv("MARKET_DATA_API_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(MarketProviderConfigurationError):
        get_configured_market_provider()
    monkeypatch.delenv("MARKET_DATA_PROVIDER")
    get_settings.cache_clear()


def test_live_provider_can_be_selected_with_key(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "polygon")
    monkeypatch.setenv("MARKET_DATA_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = get_configured_market_provider()
    assert provider.name == "polygon"
    monkeypatch.delenv("MARKET_DATA_PROVIDER")
    monkeypatch.delenv("MARKET_DATA_API_KEY")
    get_settings.cache_clear()


def test_twelve_data_provider_can_be_selected(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "twelve_data")
    monkeypatch.setenv("MARKET_DATA_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = get_configured_market_provider()
    assert provider.name == "twelve_data"
    monkeypatch.delenv("MARKET_DATA_PROVIDER")
    monkeypatch.delenv("MARKET_DATA_API_KEY")
    get_settings.cache_clear()


def test_live_market_provider_stubs_raise_not_implemented():
    provider = LiveMarketDataProvider(name="polygon", api_key="test-key")
    with pytest.raises(NotImplementedError):
        provider.get_quote("AAPL")
    with pytest.raises(NotImplementedError):
        provider.get_historical_prices("AAPL")
