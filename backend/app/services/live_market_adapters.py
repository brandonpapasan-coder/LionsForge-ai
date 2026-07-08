from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from app.schemas.market import HistoricalPriceRead, QuoteRead, utc_now
from app.services.market_providers import MarketDataProvider, normalize_symbol


class MarketDataProviderError(RuntimeError):
    pass


class TwelveDataMarketProvider(MarketDataProvider):
    name = "twelve_data"
    base_url = "https://api.twelvedata.com"

    def __init__(self, api_key: str, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {**params, "apikey": self.api_key}
        try:
            response = httpx.get(
                f"{self.base_url}{path}", params=request_params, timeout=self.timeout_seconds
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(f"Twelve Data request failed: {exc}") from exc

        payload = response.json()
        if isinstance(payload, dict) and payload.get("status") == "error":
            message = payload.get("message", "unknown provider error")
            raise MarketDataProviderError(f"Twelve Data error: {message}")
        return payload

    def get_quote(self, symbol: str) -> QuoteRead:
        normalized = normalize_symbol(symbol)
        payload = self._get("/quote", {"symbol": normalized})
        price_value = payload.get("close") or payload.get("price")
        if price_value is None:
            raise MarketDataProviderError("Twelve Data quote response did not include a price")
        return QuoteRead(
            symbol=normalized,
            price=Decimal(str(price_value)),
            currency="USD",
            source=self.name,
            as_of=utc_now(),
            is_delayed=True,
        )

    def get_historical_prices(self, symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
        normalized = normalize_symbol(symbol)
        payload = self._get(
            "/time_series",
            {"symbol": normalized, "interval": "1day", "outputsize": limit, "format": "JSON"},
        )
        values = payload.get("values")
        if not isinstance(values, list):
            raise MarketDataProviderError("Twelve Data historical response did not include values")

        prices: list[HistoricalPriceRead] = []
        for item in reversed(values[:limit]):
            prices.append(
                HistoricalPriceRead(
                    symbol=normalized,
                    date=date.fromisoformat(str(item["datetime"])),
                    open=Decimal(str(item["open"])),
                    high=Decimal(str(item["high"])),
                    low=Decimal(str(item["low"])),
                    close=Decimal(str(item["close"])),
                    volume=int(Decimal(str(item.get("volume", "0")))),
                    source=self.name,
                    is_adjusted=True,
                )
            )
        return prices
