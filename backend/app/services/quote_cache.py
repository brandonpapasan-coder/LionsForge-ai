from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.schemas.market import QuoteRead


class RedisLikeClient(Protocol):
    def get(self, key: str) -> str | bytes | None: ...

    def setex(self, key: str, ttl: int, value: str) -> object: ...

    def delete(self, key: str) -> object: ...


class QuoteCache:
    def __init__(self, ttl_seconds: int = 30, redis_client: RedisLikeClient | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self.ttl = timedelta(seconds=ttl_seconds)
        self.redis_client = redis_client
        self._items: dict[str, tuple[datetime, QuoteRead]] = {}

    def _key(self, symbol: str) -> str:
        return f"quote:{symbol.upper().strip()}"

    def get(self, symbol: str) -> QuoteRead | None:
        key = symbol.upper().strip()
        if self.redis_client is not None:
            cached_payload = self.redis_client.get(self._key(key))
            if cached_payload is None:
                return None
            if isinstance(cached_payload, bytes):
                cached_payload = cached_payload.decode("utf-8")
            return QuoteRead.model_validate_json(cached_payload)

        cached = self._items.get(key)
        if cached is None:
            return None
        created_at, quote = cached
        if datetime.now(timezone.utc) - created_at > self.ttl:
            self._items.pop(key, None)
            return None
        return quote

    def set(self, quote: QuoteRead) -> QuoteRead:
        key = quote.symbol.upper()
        if self.redis_client is not None:
            self.redis_client.setex(self._key(key), self.ttl_seconds, quote.model_dump_json())
            return quote
        self._items[key] = (datetime.now(timezone.utc), quote)
        return quote

    def clear(self) -> None:
        self._items.clear()

    def clear_symbol(self, symbol: str) -> None:
        key = symbol.upper().strip()
        self._items.pop(key, None)
        if self.redis_client is not None:
            self.redis_client.delete(self._key(key))


quote_cache = QuoteCache()
