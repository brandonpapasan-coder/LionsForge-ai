from decimal import Decimal

from pydantic import BaseModel


class PortfolioValue(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    total_market_value: Decimal
