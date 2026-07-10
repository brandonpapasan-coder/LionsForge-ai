from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PortfolioHoldingIntelligence(BaseModel):
    symbol: str
    allocation_percent: Decimal
    opportunity_score: Decimal
    risk_score: Decimal
    confidence_score: Decimal
    action: str
    priority: str
    attention_level: Literal["low", "medium", "high"]
    rationale: str


class PortfolioRiskHeatmapItem(BaseModel):
    symbol: str
    allocation_percent: Decimal
    decision_risk_score: Decimal
    weighted_risk_score: Decimal
    severity: Literal["low", "medium", "high"]


class PortfolioAutonomousRecommendation(BaseModel):
    category: Literal["concentration", "risk", "opportunity", "monitoring"]
    priority: Literal["low", "medium", "high"]
    title: str
    explanation: str
    related_symbols: list[str]


class AutonomousPortfolioReport(BaseModel):
    portfolio_id: int
    name: str
    portfolio_health_score: Decimal
    portfolio_risk_score: Decimal
    diversification_score: Decimal
    aggregate_opportunity_score: Decimal
    aggregate_confidence_score: Decimal
    holdings_ranked: list[PortfolioHoldingIntelligence]
    risk_heatmap: list[PortfolioRiskHeatmapItem]
    recommendations: list[PortfolioAutonomousRecommendation]
