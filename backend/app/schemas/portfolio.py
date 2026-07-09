from datetime import datetime
from decimal import Decimal
from typing import Literal

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


class PortfolioTransactionCreate(BaseModel):
    transaction_type: Literal["buy", "sell", "deposit", "withdrawal"]
    symbol: str | None = Field(default=None, max_length=12)
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    cash_amount: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = Field(default=None, max_length=255)


class PortfolioTransactionRead(BaseModel):
    id: int
    portfolio_id: int
    transaction_type: str
    symbol: str | None = None
    quantity: Decimal
    price: Decimal
    cash_amount: Decimal
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioAnalyticsHolding(BaseModel):
    symbol: str
    quantity: Decimal
    average_cost: Decimal | None = None
    market_price: Decimal
    market_value: Decimal
    cost_basis: Decimal | None = None
    unrealized_gain_loss: Decimal | None = None
    allocation_percent: Decimal


class PortfolioAnalytics(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    total_market_value: Decimal
    total_cost_basis: Decimal | None = None
    total_unrealized_gain_loss: Decimal | None = None
    cash_balance: Decimal
    gross_exposure: Decimal
    largest_position_symbol: str | None = None
    largest_position_percent: Decimal
    diversification_score: Decimal
    holdings: list[PortfolioAnalyticsHolding]


class PortfolioInsight(BaseModel):
    category: str
    severity: Literal["info", "warning", "critical"]
    title: str
    summary: str
    supporting_symbols: list[str] = []
    supporting_report_ids: list[str] = []


class PortfolioInsights(BaseModel):
    portfolio_id: int
    name: str
    summary: str
    insights: list[PortfolioInsight]
    research_coverage_percent: Decimal
    watchlist_sync_recommended: bool


class WatchlistSyncResult(BaseModel):
    portfolio_id: int
    watchlist_id: int
    added_symbols: list[str]
    tickers: list[str]
