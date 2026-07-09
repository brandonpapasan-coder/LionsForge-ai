from decimal import Decimal

from pydantic import BaseModel


class HoldingValue(BaseModel):
    symbol: str
    quantity: Decimal
    market_value: Decimal
    cost_basis: Decimal | None = None
    unrealized_gain_loss: Decimal | None = None
