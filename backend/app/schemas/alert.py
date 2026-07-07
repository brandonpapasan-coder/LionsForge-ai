from decimal import Decimal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)
    condition: str = Field(..., pattern="^(above|below)$")
    target_price: Decimal = Field(..., gt=0)
    note: str | None = Field(default=None, max_length=240)


class AlertRead(BaseModel):
    id: int
    owner_id: int
    symbol: str
    condition: str
    target_price: Decimal
    note: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class AlertEvaluation(BaseModel):
    alert_id: int
    symbol: str
    condition: str
    target_price: Decimal
    current_price: Decimal
    triggered: bool
