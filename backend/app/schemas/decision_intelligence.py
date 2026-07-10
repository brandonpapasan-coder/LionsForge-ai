from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class DecisionDriver(BaseModel):
    source: Literal["factor", "research", "event", "risk"]
    label: str
    score: Decimal
    direction: Literal["positive", "neutral", "negative"]
    explanation: str


class DecisionRecommendation(BaseModel):
    symbol: str
    action: Literal["investigate", "monitor", "review_risk", "defer"]
    priority: Literal["low", "medium", "high"]
    opportunity_score: Decimal
    risk_score: Decimal
    confidence_score: Decimal
    rationale: str
    drivers: list[DecisionDriver]
    next_actions: list[str]
    limitations: list[str]
    generated_at: datetime
