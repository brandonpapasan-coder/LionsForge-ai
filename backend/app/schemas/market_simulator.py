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


class ScenarioRunCreate(BaseModel):
    scenario_name: Literal[
        "bull_market",
        "bear_market",
        "high_volatility",
        "inflation_shock",
        "rate_cut_rally",
    ]
    initial_price: Decimal = Field(gt=0, le=Decimal("1000000000"))
    steps: int = Field(default=30, ge=1, le=5000)
    seed: int = Field(default=1, ge=0, le=2147483647)


class ScenarioPointRead(BaseModel):
    step: int
    return_rate: Decimal
    price: Decimal
    shock_applied: bool


class ScenarioRunRead(BaseModel):
    scenario_name: str
    initial_price: Decimal
    final_price: Decimal
    cumulative_return: Decimal
    steps: int
    seed: int
    points: list[ScenarioPointRead]


class PortfolioStressCreate(BaseModel):
    scenario_name: Literal[
        "bull_market",
        "bear_market",
        "high_volatility",
        "inflation_shock",
        "rate_cut_rally",
    ]
    steps: int = Field(default=30, ge=1, le=5000)
    seed: int = Field(default=1, ge=0, le=2147483647)


class StressedPositionRead(BaseModel):
    symbol: str
    starting_price: Decimal
    ending_price: Decimal
    quantity: Decimal
    starting_value: Decimal
    ending_value: Decimal
    value_change: Decimal


class PortfolioStressRead(BaseModel):
    account_id: int
    scenario_name: str
    steps: int
    seed: int
    starting_equity: Decimal
    ending_equity: Decimal
    equity_change: Decimal
    projected_return: Decimal
    positions: list[StressedPositionRead]
