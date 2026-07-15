from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SimulationAccountCreate(BaseModel):
    name: str = Field(default="Primary Simulator", min_length=1, max_length=120)
    starting_cash: Decimal = Field(default=Decimal("100000.00"), gt=0, le=Decimal("1000000000"))


class SimulationAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    starting_cash: Decimal
    cash_balance: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class SimulatedTradeCreate(BaseModel):
    account_id: int
    symbol: str = Field(min_length=1, max_length=24)
    side: Literal["buy", "sell"]
    quantity: Decimal = Field(gt=0)
    execution_price: Decimal = Field(gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class SimulatedTradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal
    notional: Decimal
    executed_at: datetime


class VirtualPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    quantity: Decimal
    average_price: Decimal
    last_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class SimulationPortfolioRead(BaseModel):
    account: SimulationAccountRead
    positions: list[VirtualPositionRead]
    positions_value: Decimal
    total_equity: Decimal
    total_return: Decimal
    concentration_risk: Decimal
