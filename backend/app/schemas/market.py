from datetime import date, datetime, timezone
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


class HistoricalPriceRead(BaseModel):
    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source: str
    is_adjusted: bool = True


class HistoricalPriceRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    limit: int = Field(default=30, ge=1, le=365)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
