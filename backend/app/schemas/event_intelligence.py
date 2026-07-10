from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class MarketEvent(BaseModel):
    event_id: str
    symbol: str | None = None
    category: Literal["earnings", "filing", "analyst", "macro", "portfolio_risk", "company"]
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    summary: str
    confidence: Decimal = Field(ge=0, le=1)
    occurred_at: datetime
    source: str
    evidence: list[str]
    affected_symbols: list[str]


class MarketEventList(BaseModel):
    count: int
    events: list[MarketEvent]


class EventImpactSummary(BaseModel):
    symbol: str
    event_count: int
    highest_severity: Literal["none", "low", "medium", "high", "critical"]
    impact_score: Decimal
    events: list[MarketEvent]
    follow_up_actions: list[str]
