from decimal import Decimal

from pydantic import BaseModel


class HoldingSummary(BaseModel):
    symbol: str
    quantity: Decimal
    current_price: Decimal
    market_value: Decimal
    average_cost: Decimal | None = None
    cost_basis: Decimal | None = None
    unrealized_gain_loss: Decimal | None = None
    allocation_percent: Decimal


class PortfolioSummary(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    total_market_value: Decimal
    total_cost_basis: Decimal | None = None
    total_unrealized_gain_loss: Decimal | None = None
    holdings: list[HoldingSummary]
