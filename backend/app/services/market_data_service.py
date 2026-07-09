from app.schemas.market import HistoricalPriceRead, QuoteRead
from app.services.market_data_router import MarketDataRouter
from app.services.market_provider_health import provider_health_registry
from app.services.market_providers import MockMarketDataProvider, normalize_symbol
from app.services.provider_selector import get_configured_market_providers
from app.services.quote_cache import quote_cache


def _fallback_provider() -> MockMarketDataProvider:
    return MockMarketDataProvider()


def _router() -> MarketDataRouter:
    try:
        providers = get_configured_market_providers()
    except Exception:
        providers = [_fallback_provider()]
    if not any(provider.name == "mock-market-data" for provider in providers):
        providers.append(_fallback_provider())
    return MarketDataRouter(providers=providers, health_registry=provider_health_registry)


def get_quote(symbol: str) -> QuoteRead:
    cached = quote_cache.get(symbol)
    if cached is not None:
        return cached
    try:
        quote = _router().get_quote(symbol)
    except Exception:
        quote = _fallback_provider().get_quote(symbol)
    return quote_cache.set(quote)


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    unique_symbols = sorted({normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)})
    return [get_quote(symbol) for symbol in unique_symbols]


def get_historical_prices(symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
    normalized = normalize_symbol(symbol)
    try:
        return _router().get_historical_prices(normalized, limit=limit)
    except Exception:
        return _fallback_provider().get_historical_prices(normalized, limit=limit)


def get_provider_health() -> dict:
    return {
        name: {
            "success_count": health.success_count,
            "failure_count": health.failure_count,
            "consecutive_failures": health.consecutive_failures,
            "last_latency_ms": health.last_latency_ms,
            "last_error": health.last_error,
            "error_rate": health.error_rate,
        }
        for name, health in provider_health_registry.snapshot().items()
    }
