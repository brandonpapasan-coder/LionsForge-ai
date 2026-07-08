from decimal import Decimal

from pydantic import BaseModel


class ResearchQuoteContext(BaseModel):
    symbol: str
    price: Decimal
    currency: str
    source: str
    is_delayed: bool


class ResearchContext(BaseModel):
    ticker: str
    quote: ResearchQuoteContext
    context_notes: list[str]
