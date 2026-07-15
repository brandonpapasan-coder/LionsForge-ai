from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketLearningSessionCreate(BaseModel):
    account_id: int
    scenario_name: Literal[
        "bull_market",
        "bear_market",
        "high_volatility",
        "inflation_shock",
        "rate_cut_rally",
    ]
    steps: int = Field(default=30, ge=1, le=5000)
    seed: int = Field(default=1, ge=0, le=2147483647)
    learner_reflection: str = Field(min_length=20, max_length=4000)


class MarketLearningSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    scenario_name: str
    steps: int
    seed: int
    risk_tier: str
    projected_return: Decimal
    learner_reflection: str
    status: str
    completed_at: datetime
