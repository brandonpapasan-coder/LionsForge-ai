from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class FactorBreakdown(BaseModel):
    name: str
    raw_score: Decimal
    normalized_score: Decimal
    weight: Decimal
    contribution: Decimal
    confidence: Literal["low", "medium", "high"]
    explanation: str
    data_freshness: Literal["mock", "stale", "fresh"] = "mock"


class FactorScore(BaseModel):
    symbol: str
    composite_score: Decimal
    rank: int | None = None
    rating: Literal["avoid", "watch", "neutral", "outperform"]
    factors: list[FactorBreakdown]
    explanation: str


class FactorRankingResponse(BaseModel):
    count: int
    results: list[FactorScore]


class ScreenerRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=50)
    min_score: Decimal | None = Field(default=None, ge=0, le=100)
    rating: Literal["avoid", "watch", "neutral", "outperform"] | None = None


class FactorCompareResponse(BaseModel):
    symbols: list[str]
    leaders: list[FactorScore]
    laggards: list[FactorScore]
