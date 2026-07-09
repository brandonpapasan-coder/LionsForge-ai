from decimal import Decimal

from app.schemas.market import HistoricalPriceRead, QuoteRead, utc_now
from app.services.market_data_service import get_historical_prices, get_provider_health, get_quote, get_quotes
from app.services.market_provider_health import provider_health_registry
from app.services.quote_cache import quote_cache


class FailingMarketProvider:
    name = "failing-provider"

    def get_quote(self, symbol: str) -> QuoteRead:
        raise RuntimeError("provider unavailable")

    def get_historical_prices(self, symbol: str, limit: int = 30):
        raise RuntimeError("provider unavailable")


class SuccessfulMarketProvider:
    name = "successful-provider"

    def get_quote(self, symbol: str) -> QuoteRead:
        return QuoteRead(
            symbol=symbol.strip().upper(),
            price=Decimal("42.00"),
            currency="USD",
            source=self.name,
            as_of=utc_now(),
            is_delayed=False,
        )

    def get_historical_prices(self, symbol: str, limit: int = 30):
        return [
            HistoricalPriceRead(
                symbol=symbol.strip().upper(),
                date=utc_now().date(),
                open=Decimal("40.00"),
                high=Decimal("45.00"),
                low=Decimal("39.00"),
                close=Decimal("42.00"),
                volume=100,
                source=self.name,
                is_adjusted=True,
            )
            for _ in range(limit)
        ]


def test_quote_falls_back_when_provider_fails(monkeypatch):
    quote_cache.clear()
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [FailingMarketProvider()],
    )

    quote = get_quote("AAPL")

    assert quote.symbol == "AAPL"
    assert quote.source == "mock-market-data"


def test_historical_prices_fall_back_when_provider_fails(monkeypatch):
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [FailingMarketProvider()],
    )

    prices = get_historical_prices("AAPL", limit=3)

    assert len(prices) == 3
    assert prices[0].symbol == "AAPL"
    assert prices[0].source == "mock-market-data"


def test_quote_uses_configured_provider_and_cache(monkeypatch):
    quote_cache.clear()
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [SuccessfulMarketProvider()],
    )

    quote = get_quote("msft")
    cached_quote = get_quote("MSFT")

    assert quote.symbol == "MSFT"
    assert quote.source == "successful-provider"
    assert cached_quote.source == "successful-provider"


def test_get_quotes_deduplicates_and_normalizes_symbols(monkeypatch):
    quote_cache.clear()
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [SuccessfulMarketProvider()],
    )

    quotes = get_quotes(["aapl", "MSFT", "aapl", ""])

    assert [quote.symbol for quote in quotes] == ["AAPL", "MSFT"]


def test_historical_prices_use_configured_provider(monkeypatch):
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [SuccessfulMarketProvider()],
    )

    prices = get_historical_prices("tsla", limit=2)

    assert len(prices) == 2
    assert prices[0].symbol == "TSLA"
    assert prices[0].source == "successful-provider"


def test_provider_health_snapshot_records_success(monkeypatch):
    quote_cache.clear()
    provider_health_registry.reset()
    monkeypatch.setattr(
        "app.services.market_data_service.get_configured_market_providers",
        lambda: [SuccessfulMarketProvider()],
    )

    get_quote("AAPL")
    health = get_provider_health()

    assert health["successful-provider"]["success_count"] == 1
    assert health["successful-provider"]["failure_count"] == 0
