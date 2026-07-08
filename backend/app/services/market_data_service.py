from app.schemas.market import QuoteRead
from app.services.provider_selector import get_configured_market_provider
from app.services.quote_cache import quote_cache


def get_quote(symbol: str) -> QuoteRead:
    cached = quote_cache.get(symbol)
    if cached is not None:
        return cached
    quote = get_configured_market_provider().get_quote(symbol)
    return quote_cache.set(quote)


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    return [get_quote(symbol) for symbol in symbols]
