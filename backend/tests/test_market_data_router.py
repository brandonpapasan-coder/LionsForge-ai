from decimal import Decimal

import pytest

from app.schemas.market import QuoteRead, utc_now
from app.services.market_data_router import MarketDataRouter, MarketDataRoutingError
from app.services.market_provider_health import ProviderHealthRegistry


class Provider:
    def __init__(self, name: str, should_fail: bool = False, price: str = "10.00") -> None:
        self.name = name
        self.should_fail = should_fail
        self.price = Decimal(price)

    def get_quote(self, symbol: str) -> QuoteRead:
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        return QuoteRead(
            symbol=symbol.upper(),
            price=self.price,
            currency="USD",
            source=self.name,
            as_of=utc_now(),
            is_delayed=False,
        )

    def get_historical_prices(self, symbol: str, limit: int = 30):
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        return []


def test_router_fails_over_to_next_provider():
    health = ProviderHealthRegistry(failure_threshold=3)
    router = MarketDataRouter(
        providers=[Provider("primary", should_fail=True), Provider("secondary", price="20.00")],
        health_registry=health,
    )

    quote = router.get_quote("aapl")

    assert quote.source == "secondary"
    assert quote.price == Decimal("20.00")
    assert health.get("primary").failure_count == 1
    assert health.get("secondary").success_count == 1


def test_router_raises_when_all_providers_fail():
    router = MarketDataRouter(
        providers=[Provider("primary", should_fail=True), Provider("secondary", should_fail=True)],
        health_registry=ProviderHealthRegistry(),
    )

    with pytest.raises(MarketDataRoutingError):
        router.get_quote("AAPL")


def test_router_skips_unhealthy_provider_until_all_are_unhealthy():
    health = ProviderHealthRegistry(failure_threshold=1)
    health.record_failure("primary", RuntimeError("down"))
    router = MarketDataRouter(
        providers=[Provider("primary"), Provider("secondary", price="30.00")],
        health_registry=health,
    )

    quote = router.get_quote("MSFT")

    assert quote.source == "secondary"
    assert quote.price == Decimal("30.00")


def test_router_requires_provider_list():
    with pytest.raises(ValueError):
        MarketDataRouter(providers=[])
