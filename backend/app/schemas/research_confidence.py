from decimal import Decimal

from pydantic import BaseModel


class ResearchConfidence(BaseModel):
    symbol: str
    item_count: int
    confidence: Decimal
    explanation: str
