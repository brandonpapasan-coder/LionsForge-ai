from decimal import Decimal

from app.schemas.market import QuoteRead, utc_now

MOCK_PRICES: dict[str, Decimal] = {
    "AAPL": Decimal("225.00"),
    "MSFT": Decimal("450.00"),
    "NVDA": Decimal("125.00"),
    "TSLA": Decimal("250.00"),
    "SPY": Decimal("550.00"),
    "QQQ": Decimal("480.00"),
}


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def get_quote(symbol: str) -> QuoteRead:
    normalized = normalize_symbol(symbol)
    price = MOCK_PRICES.get(normalized, Decimal("100.00"))
    return QuoteRead(
        symbol=normalized,
        price=price,
        currency="USD",
        source="mock-market-data",
        as_of=utc_now(),
        is_delayed=True,
    )


def get_quotes(symbols: list[str]) -> list[QuoteRead]:
    unique_symbols = sorted({normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)})
    return [get_quote(symbol) for symbol in unique_symbols]
