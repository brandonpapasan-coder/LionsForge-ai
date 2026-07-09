from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.research_report import ResearchReport as ResearchReportModel
from app.schemas.portfolio import PortfolioInsight, PortfolioInsights
from app.services.portfolio_analytics_service import build_portfolio_analytics


def _latest_report_ids_by_symbol(db: Session, portfolio: Portfolio) -> dict[str, str]:
    report_ids: dict[str, str] = {}
    for holding in portfolio.holdings:
        statement = (
            select(ResearchReportModel)
            .where(ResearchReportModel.symbol == holding.symbol)
            .order_by(ResearchReportModel.created_at.desc())
            .limit(1)
        )
        report = db.execute(statement).scalars().first()
        if report is not None:
            report_ids[holding.symbol] = report.report_id
    return report_ids


def build_portfolio_insights(db: Session, portfolio: Portfolio) -> PortfolioInsights:
    analytics = build_portfolio_analytics(portfolio)
    report_ids = _latest_report_ids_by_symbol(db, portfolio)
    insights: list[PortfolioInsight] = []

    if not analytics.holdings:
        insights.append(
            PortfolioInsight(
                category="setup",
                severity="info",
                title="Portfolio is empty",
                summary="Add holdings or transactions to begin receiving portfolio intelligence.",
            )
        )
    else:
        insights.append(
            PortfolioInsight(
                category="overview",
                severity="info",
                title="Portfolio analytics ready",
                summary=(
                    f"Portfolio market value is {analytics.total_market_value} {analytics.base_currency} "
                    f"across {len(analytics.holdings)} holding(s)."
                ),
                supporting_symbols=[holding.symbol for holding in analytics.holdings],
                supporting_report_ids=list(report_ids.values()),
            )
        )

    if analytics.largest_position_percent >= Decimal("50") and analytics.largest_position_symbol:
        insights.append(
            PortfolioInsight(
                category="concentration",
                severity="warning",
                title="High concentration detected",
                summary=(
                    f"{analytics.largest_position_symbol} represents {analytics.largest_position_percent}% "
                    "of portfolio market value. Review concentration risk before increasing exposure."
                ),
                supporting_symbols=[analytics.largest_position_symbol],
                supporting_report_ids=[report_ids[analytics.largest_position_symbol]]
                if analytics.largest_position_symbol in report_ids
                else [],
            )
        )

    if analytics.diversification_score < Decimal("40") and analytics.holdings:
        insights.append(
            PortfolioInsight(
                category="diversification",
                severity="warning",
                title="Diversification score is low",
                summary=(
                    f"Diversification score is {analytics.diversification_score}. "
                    "Consider reviewing position count and allocation balance."
                ),
                supporting_symbols=[holding.symbol for holding in analytics.holdings],
            )
        )

    covered_symbols = set(report_ids)
    research_coverage_percent = (
        (Decimal(len(covered_symbols)) / Decimal(len(portfolio.holdings))) * Decimal("100")
        if portfolio.holdings
        else Decimal("0")
    ).quantize(Decimal("0.000001"))

    if portfolio.holdings and research_coverage_percent < Decimal("100"):
        uncovered = [holding.symbol for holding in portfolio.holdings if holding.symbol not in covered_symbols]
        insights.append(
            PortfolioInsight(
                category="research_coverage",
                severity="info",
                title="Research coverage incomplete",
                summary="Generate research reports for uncovered holdings to improve AI portfolio context.",
                supporting_symbols=uncovered,
            )
        )

    return PortfolioInsights(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        summary=f"{len(insights)} portfolio insight(s) generated from holdings, market data, and research coverage.",
        insights=insights,
        research_coverage_percent=research_coverage_percent,
        watchlist_sync_recommended=bool(portfolio.holdings),
    )
