from collections import defaultdict
from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio_risk import PortfolioRiskReport, PositionRisk, RiskRecommendation, SectorExposure
from app.services.portfolio_analytics_service import (
    calculate_cash_balance,
    calculate_holding_market_value,
    calculate_total_market_value,
    normalize_percent,
)

PERCENT = Decimal("100")
ZERO = Decimal("0")

SECTOR_BY_SYMBOL = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "GOOGL": "Communication Services",
    "GOOG": "Communication Services",
    "META": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "JPM": "Financials",
    "BAC": "Financials",
    "JNJ": "Healthcare",
    "UNH": "Healthcare",
    "XOM": "Energy",
    "CVX": "Energy",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
}


def build_portfolio_risk_report(portfolio: Portfolio) -> PortfolioRiskReport:
    total_market_value = calculate_total_market_value(portfolio)
    cash_balance = calculate_cash_balance(portfolio)
    total_assets = total_market_value + cash_balance
    position_count = len(portfolio.holdings)

    if total_assets <= 0:
        return _empty_report(portfolio=portfolio, cash_balance=cash_balance)

    positions = _build_position_risks(portfolio=portfolio, total_market_value=total_market_value)
    sectors = _build_sector_exposure(portfolio=portfolio, total_market_value=total_market_value)
    largest_position = max((position.allocation_percent for position in positions), default=ZERO)
    largest_symbol = next((position.symbol for position in positions if position.allocation_percent == largest_position), None)

    diversification_score = _diversification_score(position_count=position_count, largest_position_percent=largest_position)
    concentration_score = _concentration_score(largest_position)
    cash_allocation_percent = normalize_percent((cash_balance / total_assets) * PERCENT) if total_assets > 0 else ZERO
    sector_concentration = max((sector.allocation_percent for sector in sectors), default=ZERO)

    portfolio_risk_score = _portfolio_risk_score(
        largest_position_percent=largest_position,
        sector_concentration_percent=sector_concentration,
        cash_allocation_percent=cash_allocation_percent,
        position_count=position_count,
    )
    portfolio_health_score = normalize_percent(PERCENT - portfolio_risk_score)

    return PortfolioRiskReport(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        portfolio_health_score=portfolio_health_score,
        portfolio_risk_score=portfolio_risk_score,
        diversification_score=diversification_score,
        concentration_score=concentration_score,
        total_market_value=total_market_value,
        cash_balance=cash_balance,
        cash_allocation_percent=cash_allocation_percent,
        largest_position_symbol=largest_symbol,
        largest_position_percent=largest_position,
        position_count=position_count,
        estimated_beta=_estimated_beta(position_count=position_count, largest_position_percent=largest_position),
        estimated_volatility_percent=_estimated_volatility(position_count=position_count, largest_position_percent=largest_position),
        sector_exposure=sectors,
        top_position_risks=positions[:5],
        recommendations=_build_recommendations(
            largest_position_symbol=largest_symbol,
            largest_position_percent=largest_position,
            sector_concentration_percent=sector_concentration,
            cash_allocation_percent=cash_allocation_percent,
            diversification_score=diversification_score,
            position_count=position_count,
        ),
    )


def _empty_report(portfolio: Portfolio, cash_balance: Decimal) -> PortfolioRiskReport:
    return PortfolioRiskReport(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        portfolio_health_score=Decimal("0.000000"),
        portfolio_risk_score=Decimal("100.000000"),
        diversification_score=Decimal("0.000000"),
        concentration_score=Decimal("100.000000"),
        total_market_value=Decimal("0.000000"),
        cash_balance=cash_balance,
        cash_allocation_percent=Decimal("0.000000"),
        largest_position_symbol=None,
        largest_position_percent=Decimal("0.000000"),
        position_count=0,
        estimated_beta=Decimal("0.000000"),
        estimated_volatility_percent=Decimal("0.000000"),
        sector_exposure=[],
        top_position_risks=[],
        recommendations=[
            RiskRecommendation(
                priority="high",
                category="portfolio_empty",
                metric="position_count",
                message="Portfolio has no holdings. Add holdings before risk intelligence can produce a meaningful score.",
            )
        ],
    )


def _build_position_risks(portfolio: Portfolio, total_market_value: Decimal) -> list[PositionRisk]:
    risks: list[PositionRisk] = []
    for holding in portfolio.holdings:
        market_value = calculate_holding_market_value(holding)
        allocation_percent = _allocation(market_value, total_market_value)
        risks.append(
            PositionRisk(
                symbol=holding.symbol,
                sector=_sector_for(holding),
                market_value=market_value,
                allocation_percent=allocation_percent,
                risk_level=_position_risk_level(allocation_percent),
            )
        )
    return sorted(risks, key=lambda risk: risk.allocation_percent, reverse=True)


def _build_sector_exposure(portfolio: Portfolio, total_market_value: Decimal) -> list[SectorExposure]:
    sector_values: dict[str, Decimal] = defaultdict(Decimal)
    for holding in portfolio.holdings:
        sector_values[_sector_for(holding)] += calculate_holding_market_value(holding)
    sectors = [
        SectorExposure(
            sector=sector,
            market_value=value,
            allocation_percent=_allocation(value, total_market_value),
        )
        for sector, value in sector_values.items()
    ]
    return sorted(sectors, key=lambda exposure: exposure.allocation_percent, reverse=True)


def _allocation(part: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0.000000")
    return normalize_percent((part / total) * PERCENT)


def _sector_for(holding: PortfolioHolding) -> str:
    return SECTOR_BY_SYMBOL.get(holding.symbol.upper(), "Unclassified")


def _position_risk_level(allocation_percent: Decimal) -> str:
    if allocation_percent >= Decimal("40"):
        return "high"
    if allocation_percent >= Decimal("25"):
        return "medium"
    return "low"


def _diversification_score(position_count: int, largest_position_percent: Decimal) -> Decimal:
    position_score = min(Decimal(position_count) / Decimal("10"), Decimal("1")) * Decimal("50")
    concentration_score = max(ZERO, Decimal("50") - (largest_position_percent / Decimal("2")))
    return normalize_percent(min(PERCENT, position_score + concentration_score))


def _concentration_score(largest_position_percent: Decimal) -> Decimal:
    return normalize_percent(min(PERCENT, largest_position_percent))


def _portfolio_risk_score(
    largest_position_percent: Decimal,
    sector_concentration_percent: Decimal,
    cash_allocation_percent: Decimal,
    position_count: int,
) -> Decimal:
    concentration_component = largest_position_percent * Decimal("0.45")
    sector_component = sector_concentration_percent * Decimal("0.25")
    cash_component = max(ZERO, cash_allocation_percent - Decimal("20")) * Decimal("0.15")
    sparse_portfolio_component = max(ZERO, Decimal("5") - Decimal(position_count)) * Decimal("5")
    return normalize_percent(min(PERCENT, concentration_component + sector_component + cash_component + sparse_portfolio_component))


def _estimated_beta(position_count: int, largest_position_percent: Decimal) -> Decimal:
    if position_count == 0:
        return Decimal("0.000000")
    base_beta = Decimal("1.000000")
    concentration_adjustment = max(ZERO, largest_position_percent - Decimal("25")) / Decimal("100")
    return normalize_percent(base_beta + concentration_adjustment)


def _estimated_volatility(position_count: int, largest_position_percent: Decimal) -> Decimal:
    if position_count == 0:
        return Decimal("0.000000")
    base_volatility = Decimal("18.000000")
    concentration_adjustment = max(ZERO, largest_position_percent - Decimal("20")) / Decimal("2")
    diversification_adjustment = max(ZERO, Decimal("5") - Decimal(position_count)) * Decimal("2")
    return normalize_percent(base_volatility + concentration_adjustment + diversification_adjustment)


def _build_recommendations(
    largest_position_symbol: str | None,
    largest_position_percent: Decimal,
    sector_concentration_percent: Decimal,
    cash_allocation_percent: Decimal,
    diversification_score: Decimal,
    position_count: int,
) -> list[RiskRecommendation]:
    recommendations: list[RiskRecommendation] = []
    if largest_position_symbol and largest_position_percent >= Decimal("40"):
        recommendations.append(
            RiskRecommendation(
                priority="high",
                category="concentration",
                metric="largest_position_percent",
                message=f"{largest_position_symbol} represents {largest_position_percent}% of market exposure. Review concentration risk.",
            )
        )
    elif largest_position_symbol and largest_position_percent >= Decimal("25"):
        recommendations.append(
            RiskRecommendation(
                priority="medium",
                category="concentration",
                metric="largest_position_percent",
                message=f"{largest_position_symbol} is a large position at {largest_position_percent}% of market exposure.",
            )
        )

    if sector_concentration_percent >= Decimal("60"):
        recommendations.append(
            RiskRecommendation(
                priority="medium",
                category="sector_exposure",
                metric="sector_concentration_percent",
                message=f"One sector represents {sector_concentration_percent}% of market exposure. Review sector balance.",
            )
        )

    if position_count < 5:
        recommendations.append(
            RiskRecommendation(
                priority="medium",
                category="diversification",
                metric="position_count",
                message="Portfolio has fewer than five holdings. Additional diversified positions may reduce idiosyncratic risk.",
            )
        )

    if cash_allocation_percent >= Decimal("40"):
        recommendations.append(
            RiskRecommendation(
                priority="low",
                category="cash_allocation",
                metric="cash_allocation_percent",
                message=f"Cash allocation is {cash_allocation_percent}%. Review whether idle cash matches the portfolio objective.",
            )
        )

    if diversification_score < Decimal("50"):
        recommendations.append(
            RiskRecommendation(
                priority="medium",
                category="diversification",
                metric="diversification_score",
                message="Diversification score is below 50. Review position count and concentration before adding risk.",
            )
        )

    if not recommendations:
        recommendations.append(
            RiskRecommendation(
                priority="low",
                category="portfolio_health",
                metric="portfolio_health_score",
                message="No major deterministic risk rule was triggered. Continue monitoring allocations and research freshness.",
            )
        )
    return recommendations
