from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class SectorExposure(BaseModel):
    sector: str
    market_value: Decimal
    allocation_percent: Decimal


class PositionRisk(BaseModel):
    symbol: str
    sector: str
    market_value: Decimal
    allocation_percent: Decimal
    risk_level: Literal["low", "medium", "high"]


class RiskRecommendation(BaseModel):
    priority: Literal["low", "medium", "high"]
    category: str
    metric: str
    message: str


class PortfolioRiskReport(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    portfolio_health_score: Decimal
    portfolio_risk_score: Decimal
    diversification_score: Decimal
    concentration_score: Decimal
    total_market_value: Decimal
    cash_balance: Decimal
    cash_allocation_percent: Decimal
    largest_position_symbol: str | None = None
    largest_position_percent: Decimal
    position_count: int
    estimated_beta: Decimal
    estimated_volatility_percent: Decimal
    sector_exposure: list[SectorExposure]
    top_position_risks: list[PositionRisk]
    recommendations: list[RiskRecommendation]
