from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field


class QuoteRead(BaseModel):
    symbol: str
    price: Decimal
    currency: str = "USD"
    source: str
    as_of: datetime
    is_delayed: bool = True


class QuoteRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=50)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
