from decimal import Decimal

from app.models.portfolio import Portfolio
from app.services.market_data_service import get_quote


def calculate_total_market_value(portfolio: Portfolio) -> Decimal:
    total = Decimal("0")
    for holding in portfolio.holdings:
        quote = get_quote(holding.symbol)
        total += holding.quantity * quote.price
    return total
