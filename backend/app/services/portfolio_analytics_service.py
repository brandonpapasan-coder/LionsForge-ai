from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioHolding
from app.services.market_data_service import get_quote


def calculate_holding_market_value(holding: PortfolioHolding) -> Decimal:
    quote = get_quote(holding.symbol)
    return holding.quantity * quote.price


def calculate_total_market_value(portfolio: Portfolio) -> Decimal:
    total = Decimal("0")
    for holding in portfolio.holdings:
        total += calculate_holding_market_value(holding)
    return total
