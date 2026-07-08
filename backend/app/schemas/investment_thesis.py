from decimal import Decimal

from pydantic import BaseModel


class InvestmentThesis(BaseModel):
    symbol: str
    summary: str
    bull_case: list[str]
    bear_case: list[str]
    risks: list[str]
    catalysts: list[str]
    confidence: Decimal
    evidence_count: int
    supporting_evidence_ids: list[str]
