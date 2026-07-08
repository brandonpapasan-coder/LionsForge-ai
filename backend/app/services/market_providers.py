from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal

from app.schemas.market import HistoricalPriceRead, QuoteRead, utc_now


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def get_quote(self, symbol: str) -> QuoteRead:
        raise NotImplementedError

    @abstractmethod
    def get_historical_prices(self, symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
        raise NotImplementedError

    def get_quotes(self, symbols: list[str]) -> list[QuoteRead]:
        unique_symbols = sorted({normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)})
        return [self.get_quote(symbol) for symbol in unique_symbols]


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


class LiveMarketDataProvider(MarketDataProvider):
    def __init__(self, name: str, api_key: str | None = None) -> None:
        self.name = name
        self.api_key = api_key

    def get_quote(self, symbol: str) -> QuoteRead:
        raise NotImplementedError(f"Live provider '{self.name}' is not implemented yet")

    def get_historical_prices(self, symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
        raise NotImplementedError(f"Live provider '{self.name}' is not implemented yet")


class MockMarketDataProvider(MarketDataProvider):
    name = "mock-market-data"

    prices: dict[str, Decimal] = {
        "AAPL": Decimal("225.00"),
        "MSFT": Decimal("450.00"),
        "NVDA": Decimal("125.00"),
        "TSLA": Decimal("250.00"),
        "SPY": Decimal("550.00"),
        "QQQ": Decimal("480.00"),
    }

    def get_quote(self, symbol: str) -> QuoteRead:
        normalized = normalize_symbol(symbol)
        return QuoteRead(
            symbol=normalized,
            price=self.prices.get(normalized, Decimal("100.00")),
            currency="USD",
            source=self.name,
            as_of=utc_now(),
            is_delayed=True,
        )

    def get_historical_prices(self, symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
        normalized = normalize_symbol(symbol)
        close_price = self.prices.get(normalized, Decimal("100.00"))
        today = utc_now().date()
        prices: list[HistoricalPriceRead] = []
        for offset in range(limit):
            day = today - timedelta(days=limit - offset - 1)
            drift = Decimal(offset) / Decimal("10")
            close = close_price + drift
            prices.append(
                HistoricalPriceRead(
                    symbol=normalized,
                    date=day,
                    open=close - Decimal("1.00"),
                    high=close + Decimal("2.00"),
                    low=close - Decimal("2.00"),
                    close=close,
                    volume=1_000_000 + offset,
                    source=self.name,
                    is_adjusted=True,
                )
            )
        return prices
