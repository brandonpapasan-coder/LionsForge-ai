from app.schemas.market import QuoteRead, utc_now
from app.services.market_data_service import get_historical_prices, get_quote
from app.services.quote_cache import quote_cache


class FailingMarketProvider:
    name = "failing-provider"

    def get_quote(self, symbol: str) -> QuoteRead:
        raise RuntimeError("provider unavailable")

    def get_historical_prices(self, symbol: str, limit: int = 30):
        raise RuntimeError("provider unavailable")


def test_quote_falls_back_when_provider_fails(monkeypatch):
    quote_cache._quotes.clear()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_provider",
        lambda: FailingMarketProvider(),
    )

    quote = get_quote("AAPL")

    assert quote.symbol == "AAPL"
    assert quote.source == "mock-market-data"


def test_historical_prices_fall_back_when_provider_fails(monkeypatch):
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_provider",
        lambda: FailingMarketProvider(),
    )

    prices = get_historical_prices("AAPL", limit=3)

    assert len(prices) == 3
    assert prices[0].symbol == "AAPL"
    assert prices[0].source == "mock-market-data"
