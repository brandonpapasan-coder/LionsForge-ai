from decimal import Decimal

from pydantic import BaseModel


class HoldingAllocation(BaseModel):
    symbol: str
    market_value: Decimal
    allocation_percent: Decimal
