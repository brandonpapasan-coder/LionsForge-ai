from decimal import Decimal

from pydantic import BaseModel


class PortfolioPerformance(BaseModel):
    portfolio_id: int
    total_market_value: Decimal
    total_cost_basis: Decimal | None = None
    total_unrealized_gain_loss: Decimal | None = None
