from decimal import Decimal

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)
    quantity: Decimal = Field(..., gt=0)
    average_cost: Decimal | None = Field(default=None, ge=0)


class HoldingRead(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    quantity: Decimal
    average_cost: Decimal | None = None

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)


class PortfolioRead(BaseModel):
    id: int
    owner_id: int
    name: str
    base_currency: str
    holdings: list[HoldingRead] = []

    model_config = {"from_attributes": True}
