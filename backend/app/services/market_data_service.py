from app.schemas.market import QuoteRead
from app.services.market_providers import MockMarketDataProvider

provider = MockMarketDataProvider()


def get_quote(symbol: str) -> QuoteRead:
    return provider.get_quote(symbol)


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    return provider.get_quotes(symbols)
