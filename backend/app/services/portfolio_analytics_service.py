from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio import PortfolioAnalytics, PortfolioAnalyticsHolding
from app.services.market_data_service import get_quote

MONEY_PRECISION = Decimal("0.000001")
PERCENT_PRECISION = Decimal("0.000001")


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def normalize_percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_PRECISION)


def calculate_holding_market_price(holding: PortfolioHolding) -> Decimal:
    return get_quote(holding.symbol).price


def calculate_holding_market_value(holding: PortfolioHolding) -> Decimal:
    return normalize_money(holding.quantity * calculate_holding_market_price(holding))


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


def calculate_cash_balance(portfolio: Portfolio) -> Decimal:
    cash = Decimal("0")
    for transaction in portfolio.transactions:
        if transaction.transaction_type == "deposit":
            cash += transaction.cash_amount
        elif transaction.transaction_type in {"withdrawal", "buy"}:
            cash -= transaction.cash_amount
        elif transaction.transaction_type == "sell":
            cash += transaction.cash_amount
    return normalize_money(cash)


def calculate_diversification_score(portfolio: Portfolio) -> Decimal:
    if not portfolio.holdings:
        return Decimal("0.000000")
    largest_allocation = max(calculate_allocation_percent(holding, portfolio) for holding in portfolio.holdings)
    position_count_score = min(Decimal(len(portfolio.holdings)) / Decimal("10"), Decimal("1")) * Decimal("50")
    concentration_score = max(Decimal("0"), Decimal("50") - (largest_allocation / Decimal("2")))
    return normalize_percent(position_count_score + concentration_score)


def build_portfolio_analytics(portfolio: Portfolio) -> PortfolioAnalytics:
    total_market_value = calculate_total_market_value(portfolio)
    analytics_holdings: list[PortfolioAnalyticsHolding] = []
    largest_symbol: str | None = None
    largest_percent = Decimal("0")

    for holding in portfolio.holdings:
        market_price = calculate_holding_market_price(holding)
        market_value = calculate_holding_market_value(holding)
        allocation_percent = calculate_allocation_percent(holding, portfolio)
        if allocation_percent > largest_percent:
            largest_percent = allocation_percent
            largest_symbol = holding.symbol
        analytics_holdings.append(
            PortfolioAnalyticsHolding(
                symbol=holding.symbol,
                quantity=holding.quantity,
                average_cost=holding.average_cost,
                market_price=market_price,
                market_value=market_value,
                cost_basis=calculate_holding_cost_basis(holding),
                unrealized_gain_loss=calculate_holding_gain_loss(holding),
                allocation_percent=allocation_percent,
            )
        )

    return PortfolioAnalytics(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        total_market_value=total_market_value,
        total_cost_basis=calculate_total_cost_basis(portfolio),
        total_unrealized_gain_loss=calculate_total_gain_loss(portfolio),
        cash_balance=calculate_cash_balance(portfolio),
        gross_exposure=total_market_value,
        largest_position_symbol=largest_symbol,
        largest_position_percent=largest_percent,
        diversification_score=calculate_diversification_score(portfolio),
        holdings=analytics_holdings,
    )
