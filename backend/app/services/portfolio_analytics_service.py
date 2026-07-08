from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioHolding
from app.services.market_data_service import get_quote

MONEY_PRECISION = Decimal("0.000001")
PERCENT_PRECISION = Decimal("0.000001")


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def normalize_percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_PRECISION)


def calculate_holding_market_value(holding: PortfolioHolding) -> Decimal:
    quote = get_quote(holding.symbol)
    return normalize_money(holding.quantity * quote.price)


def calculate_holding_cost_basis(holding: PortfolioHolding) -> Decimal | None:
    if holding.average_cost is None:
        return None
    return normalize_money(holding.quantity * holding.average_cost)


def calculate_holding_gain_loss(holding: PortfolioHolding) -> Decimal | None:
    cost_basis = calculate_holding_cost_basis(holding)
    if cost_basis is None:
        return None
    return normalize_money(calculate_holding_market_value(holding) - cost_basis)


def calculate_total_market_value(portfolio: Portfolio) -> Decimal:
    total = Decimal("0")
    for holding in portfolio.holdings:
        total += calculate_holding_market_value(holding)
    return normalize_money(total)


def calculate_total_cost_basis(portfolio: Portfolio) -> Decimal | None:
    total = Decimal("0")
    has_cost_basis = False
    for holding in portfolio.holdings:
        cost_basis = calculate_holding_cost_basis(holding)
        if cost_basis is not None:
            has_cost_basis = True
            total += cost_basis
    return normalize_money(total) if has_cost_basis else None


def calculate_total_gain_loss(portfolio: Portfolio) -> Decimal | None:
    cost_basis = calculate_total_cost_basis(portfolio)
    if cost_basis is None:
        return None
    return normalize_money(calculate_total_market_value(portfolio) - cost_basis)


def calculate_allocation_percent(holding: PortfolioHolding, portfolio: Portfolio) -> Decimal:
    total = calculate_total_market_value(portfolio)
    if total <= 0:
        return Decimal("0")
    return normalize_percent((calculate_holding_market_value(holding) / total) * Decimal("100"))
