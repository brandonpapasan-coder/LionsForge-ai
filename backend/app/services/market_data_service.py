from app.schemas.market import QuoteRead
from app.services.provider_selector import get_configured_market_provider


def get_quote(symbol: str) -> QuoteRead:
    return get_configured_market_provider().get_quote(symbol)


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    return get_configured_market_provider().get_quotes(symbols)
