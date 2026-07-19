from app.core.legacy_market_config import get_legacy_market_settings
from app.services.live_market_adapters import TwelveDataMarketProvider
from app.services.market_providers import LiveMarketDataProvider, MarketDataProvider, MockMarketDataProvider


class MarketProviderConfigurationError(ValueError):
    pass


LIVE_PROVIDER_NAMES = {"alpaca", "polygon", "finnhub", "twelve_data"}
SUPPORTED_PROVIDER_NAMES = LIVE_PROVIDER_NAMES | {"mock"}


def _parse_provider_names(primary_provider: str, failover_providers: str) -> list[str]:
    raw_names = [primary_provider, *failover_providers.split(",")]
    normalized_names: list[str] = []
    for raw_name in raw_names:
        provider_name = raw_name.lower().strip()
        if provider_name and provider_name not in normalized_names:
            normalized_names.append(provider_name)
    return normalized_names


def _build_provider(provider_name: str, api_key: str | None) -> MarketDataProvider:
    if provider_name == "mock":
        return MockMarketDataProvider()

    if provider_name in LIVE_PROVIDER_NAMES:
        if not api_key:
            raise MarketProviderConfigurationError(f"{provider_name} requires MARKET_DATA_API_KEY")
        if provider_name == "twelve_data":
            return TwelveDataMarketProvider(api_key=api_key)
        return LiveMarketDataProvider(name=provider_name, api_key=api_key)

    raise MarketProviderConfigurationError(f"Unsupported market data provider: {provider_name}")


def get_configured_market_provider() -> MarketDataProvider:
    return get_configured_market_providers()[0]


def get_configured_market_providers() -> list[MarketDataProvider]:
    settings = get_legacy_market_settings()
    provider_names = _parse_provider_names(
        settings.market_data_provider, settings.market_data_failover_providers
    )

    if not provider_names:
        provider_names = ["mock"]

    unsupported = [name for name in provider_names if name not in SUPPORTED_PROVIDER_NAMES]
    if unsupported:
        raise MarketProviderConfigurationError(
            f"Unsupported market data provider: {unsupported[0]}"
        )

    return [_build_provider(provider_name, settings.market_data_api_key) for provider_name in provider_names]
