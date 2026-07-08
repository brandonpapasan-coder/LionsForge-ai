from app.core.config import get_settings
from app.services.market_providers import MarketDataProvider, MockMarketDataProvider


class MarketProviderConfigurationError(ValueError):
    pass


def get_configured_market_provider() -> MarketDataProvider:
    settings = get_settings()
    provider_name = settings.market_data_provider.lower().strip()

    if provider_name == "mock":
        return MockMarketDataProvider()

    raise MarketProviderConfigurationError(f"Unsupported market data provider: {provider_name}")
