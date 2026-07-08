from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    symbol: str
    category: str
    source: str
    title: str
    observed_at: datetime
    confidence: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCollection(BaseModel):
    symbol: str
    items: list[EvidenceItem]
