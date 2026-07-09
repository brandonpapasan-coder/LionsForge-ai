from decimal import Decimal

from app.schemas.market import QuoteRead, utc_now
from app.services.quote_cache import QuoteCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl

    def delete(self, key: str):
        self.values.pop(key, None)


def make_quote(symbol: str = "AAPL") -> QuoteRead:
    return QuoteRead(
        symbol=symbol,
        price=Decimal("123.45"),
        currency="USD",
        source="test",
        as_of=utc_now(),
        is_delayed=False,
    )


def test_redis_cache_set_get_and_clear_symbol():
    redis = FakeRedis()
    cache = QuoteCache(ttl_seconds=45, redis_client=redis)

    quote = cache.set(make_quote())
    cached = cache.get("aapl")

    assert cached == quote
    assert redis.ttls["quote:AAPL"] == 45

    cache.clear_symbol("AAPL")
    assert cache.get("AAPL") is None
