from app.core.config import get_settings
from app.services.market_providers import LiveMarketDataProvider, MarketDataProvider, MockMarketDataProvider


class MarketProviderConfigurationError(ValueError):
    pass


LIVE_PROVIDER_NAMES = {"alpaca", "polygon", "finnhub", "twelve_data"}


def get_configured_market_provider() -> MarketDataProvider:
    settings = get_settings()
    provider_name = settings.market_data_provider.lower().strip()

    if provider_name == "mock":
        return MockMarketDataProvider()

    if provider_name in LIVE_PROVIDER_NAMES:
        if not settings.market_data_api_key:
            raise MarketProviderConfigurationError(f"{provider_name} requires MARKET_DATA_API_KEY")
        return LiveMarketDataProvider(name=provider_name, api_key=settings.market_data_api_key)

    raise MarketProviderConfigurationError(f"Unsupported market data provider: {provider_name}")
