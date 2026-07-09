from app.services.market_data_service import get_quote, get_quotes
from app.services.quote_cache import quote_cache


def test_quote_cache_reuses_single_quote():
    quote_cache.clear()
    first = get_quote("AAPL")
    second = get_quote("aapl")
    assert first.symbol == "AAPL"
    assert second.symbol == "AAPL"
    assert first.as_of == second.as_of


def test_batch_quotes_are_deduplicated():
    quote_cache.clear()
    quotes = get_quotes(["AAPL", "aapl", "MSFT"])
    assert [quote.symbol for quote in quotes] == ["AAPL", "MSFT"]
