from decimal import Decimal

from pydantic import BaseModel


class ResearchQuoteContext(BaseModel):
    symbol: str
    price: Decimal
    currency: str
    source: str
    is_delayed: bool


class ResearchNewsContext(BaseModel):
    title: str
    source: str
    summary: str | None = None


class ResearchContext(BaseModel):
    ticker: str
    quote: ResearchQuoteContext
    news: list[ResearchNewsContext]
    context_notes: list[str]
