from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class ResearchAgentFinding(BaseModel):
    category: Literal["strength", "risk", "opportunity", "question"]
    title: str
    summary: str
    evidence: list[str]
    confidence: Decimal


class ResearchAgentReport(BaseModel):
    symbol: str
    business_summary: str
    market_context: str
    factor_score: Decimal
    factor_rating: str
    confidence_score: Decimal
    freshness: Literal["mock", "stale", "fresh"]
    findings: list[ResearchAgentFinding]
    bull_case: str
    bear_case: str
    open_questions: list[str]
    limitations: list[str]
    generated_at: datetime
