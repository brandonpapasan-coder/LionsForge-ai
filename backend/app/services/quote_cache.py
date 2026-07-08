from datetime import datetime, timedelta, timezone

from app.schemas.market import QuoteRead


class QuoteCache:
    def __init__(self, ttl_seconds: int = 30) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, tuple[datetime, QuoteRead]] = {}

    def get(self, symbol: str) -> QuoteRead | None:
        key = symbol.upper().strip()
        cached = self._items.get(key)
        if cached is None:
            return None
        created_at, quote = cached
        if datetime.now(timezone.utc) - created_at > self.ttl:
            self._items.pop(key, None)
            return None
        return quote

    def set(self, quote: QuoteRead) -> QuoteRead:
        self._items[quote.symbol.upper()] = (datetime.now(timezone.utc), quote)
        return quote

    def clear(self) -> None:
        self._items.clear()


quote_cache = QuoteCache()
