from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.live_market_adapters import MarketDataProviderError, TwelveDataMarketProvider


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "request failed",
                request=httpx.Request("GET", "https://api.twelvedata.com/test"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self.payload


def test_twelve_data_quote_mapping(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"close": "123.45"})

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    quote = provider.get_quote("aapl")

    assert quote.symbol == "AAPL"
    assert quote.price == Decimal("123.45")
    assert quote.source == "twelve_data"
    assert quote.is_delayed is True


def test_twelve_data_quote_uses_price_when_close_missing(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"price": "124.56"})

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    quote = provider.get_quote("msft")

    assert quote.symbol == "MSFT"
    assert quote.price == Decimal("124.56")


def test_twelve_data_historical_mapping(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse(
            {
                "values": [
                    {
                        "datetime": "2026-07-08",
                        "open": "100.00",
                        "high": "110.00",
                        "low": "95.00",
                        "close": "105.00",
                        "volume": "12345",
                    },
                    {
                        "datetime": "2026-07-07",
                        "open": "90.00",
                        "high": "101.00",
                        "low": "89.00",
                        "close": "100.00",
                        "volume": "10000",
                    },
                ]
            }
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    prices = provider.get_historical_prices("aapl", limit=2)

    assert len(prices) == 2
    assert prices[0].symbol == "AAPL"
    assert prices[0].date == date(2026, 7, 7)
    assert prices[0].close == Decimal("100.00")
    assert prices[1].date == date(2026, 7, 8)
    assert prices[1].source == "twelve_data"


def test_twelve_data_historical_defaults_missing_volume(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse(
            {
                "values": [
                    {
                        "datetime": "2026-07-08",
                        "open": "100.00",
                        "high": "110.00",
                        "low": "95.00",
                        "close": "105.00",
                    }
                ]
            }
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    prices = provider.get_historical_prices("nvda", limit=1)

    assert prices[0].symbol == "NVDA"
    assert prices[0].volume == 0


def test_twelve_data_provider_error_response(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"status": "error", "message": "bad symbol"})

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    with pytest.raises(MarketDataProviderError):
        provider.get_quote("BAD")


def test_twelve_data_http_error_raises_provider_error(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"message": "server error"}, status_code=500)

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    with pytest.raises(MarketDataProviderError):
        provider.get_quote("AAPL")


def test_twelve_data_missing_quote_price_raises(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"symbol": "AAPL"})

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    with pytest.raises(MarketDataProviderError):
        provider.get_quote("AAPL")


def test_twelve_data_missing_historical_values_raises(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"symbol": "AAPL"})

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = TwelveDataMarketProvider(api_key="test-key")

    with pytest.raises(MarketDataProviderError):
        provider.get_historical_prices("AAPL")
