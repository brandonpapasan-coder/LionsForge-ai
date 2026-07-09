from app.schemas.market import HistoricalPriceRead, QuoteRead
from app.services.market_providers import MockMarketDataProvider, normalize_symbol
from app.services.provider_selector import get_configured_market_provider
from app.services.quote_cache import quote_cache


def _fallback_provider() -> MockMarketDataProvider:
    return MockMarketDataProvider()


def get_quote(symbol: str) -> QuoteRead:
    cached = quote_cache.get(symbol)
    if cached is not None:
        return cached
    try:
        quote = get_configured_market_provider().get_quote(symbol)
    except Exception:
        quote = _fallback_provider().get_quote(symbol)
    return quote_cache.set(quote)


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    unique_symbols = sorted({normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)})
    return [get_quote(symbol) for symbol in unique_symbols]


def get_historical_prices(symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
    normalized = normalize_symbol(symbol)
    try:
        return get_configured_market_provider().get_historical_prices(normalized, limit=limit)
    except Exception:
        return _fallback_provider().get_historical_prices(normalized, limit=limit)
