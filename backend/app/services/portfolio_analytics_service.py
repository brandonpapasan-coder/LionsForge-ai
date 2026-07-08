from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioHolding
from app.services.market_data_service import get_quote


def calculate_holding_market_value(holding: PortfolioHolding) -> Decimal:
    quote = get_quote(holding.symbol)
    return holding.quantity * quote.price


def calculate_holding_cost_basis(holding: PortfolioHolding) -> Decimal | None:
    if holding.average_cost is None:
        return None
    return holding.quantity * holding.average_cost


def calculate_holding_gain_loss(holding: PortfolioHolding) -> Decimal | None:
    cost_basis = calculate_holding_cost_basis(holding)
    if cost_basis is None:
        return None
    return calculate_holding_market_value(holding) - cost_basis


def calculate_total_market_value(portfolio: Portfolio) -> Decimal:
    total = Decimal("0")
    for holding in portfolio.holdings:
        total += calculate_holding_market_value(holding)
    return total
