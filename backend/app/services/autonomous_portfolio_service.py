from decimal import Decimal

from app.models.portfolio import Portfolio
from app.schemas.autonomous_portfolio import (
    AutonomousPortfolioReport,
    PortfolioAutonomousRecommendation,
    PortfolioHoldingIntelligence,
    PortfolioRiskHeatmapItem,
)
from app.services.decision_intelligence_service import build_decision_recommendation
from app.services.portfolio_analytics_service import calculate_allocation_percent
from app.services.portfolio_risk_service import build_portfolio_risk_report

ZERO = Decimal("0")


def build_autonomous_portfolio_report(portfolio: Portfolio) -> AutonomousPortfolioReport:
    risk_report = build_portfolio_risk_report(portfolio)
    ranked: list[PortfolioHoldingIntelligence] = []
    heatmap: list[PortfolioRiskHeatmapItem] = []

    for holding in portfolio.holdings:
        allocation = calculate_allocation_percent(holding, portfolio)
        decision = build_decision_recommendation(holding.symbol)
        attention = _attention_level(allocation, decision.risk_score)
        ranked.append(
            PortfolioHoldingIntelligence(
                symbol=holding.symbol,
                allocation_percent=allocation,
                opportunity_score=decision.opportunity_score,
                risk_score=decision.risk_score,
                confidence_score=decision.confidence_score,
                action=decision.action,
                priority=decision.priority,
                attention_level=attention,
                rationale=decision.rationale,
            )
        )
        weighted_risk = ((allocation / Decimal("100")) * decision.risk_score).quantize(Decimal("0.000001"))
        heatmap.append(
            PortfolioRiskHeatmapItem(
                symbol=holding.symbol,
                allocation_percent=allocation,
                decision_risk_score=decision.risk_score,
                weighted_risk_score=weighted_risk,
                severity=attention,
            )
        )

    ranked.sort(key=lambda item: (item.opportunity_score, item.confidence_score), reverse=True)
    heatmap.sort(key=lambda item: item.weighted_risk_score, reverse=True)

    aggregate_opportunity = _weighted_average(ranked, "opportunity_score")
    aggregate_confidence = _weighted_average(ranked, "confidence_score")

    return AutonomousPortfolioReport(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        portfolio_health_score=risk_report.portfolio_health_score,
        portfolio_risk_score=risk_report.portfolio_risk_score,
        diversification_score=risk_report.diversification_score,
        aggregate_opportunity_score=aggregate_opportunity,
        aggregate_confidence_score=aggregate_confidence,
        holdings_ranked=ranked,
        risk_heatmap=heatmap,
        recommendations=_recommendations(risk_report, ranked, heatmap),
    )


def _weighted_average(items: list[PortfolioHoldingIntelligence], field: str) -> Decimal:
    if not items:
        return Decimal("0.000000")
    total_weight = sum((item.allocation_percent for item in items), ZERO)
    if total_weight <= 0:
        return Decimal("0.000000")
    weighted = sum((getattr(item, field) * item.allocation_percent for item in items), ZERO)
    return (weighted / total_weight).quantize(Decimal("0.000001"))


def _attention_level(allocation: Decimal, risk: Decimal) -> str:
    if allocation >= Decimal("35") or risk >= Decimal("65"):
        return "high"
    if allocation >= Decimal("20") or risk >= Decimal("45"):
        return "medium"
    return "low"


def _recommendations(risk_report, ranked, heatmap) -> list[PortfolioAutonomousRecommendation]:
    recommendations: list[PortfolioAutonomousRecommendation] = []
    if risk_report.largest_position_percent >= Decimal("35"):
        recommendations.append(
            PortfolioAutonomousRecommendation(
                category="concentration",
                priority="high",
                title="Review position concentration",
                explanation=f"{risk_report.largest_position_symbol} represents {risk_report.largest_position_percent}% of market exposure.",
                related_symbols=[risk_report.largest_position_symbol] if risk_report.largest_position_symbol else [],
            )
        )
    high_risk = [item.symbol for item in heatmap if item.severity == "high"]
    if high_risk:
        recommendations.append(
            PortfolioAutonomousRecommendation(
                category="risk",
                priority="high",
                title="Review high-attention holdings",
                explanation="These holdings combine material allocation or elevated decision risk.",
                related_symbols=high_risk,
            )
        )
    strong = [item.symbol for item in ranked if item.opportunity_score >= Decimal("70") and item.confidence_score >= Decimal("65")]
    if strong:
        recommendations.append(
            PortfolioAutonomousRecommendation(
                category="opportunity",
                priority="medium",
                title="Validate highest-ranked opportunities",
                explanation="Confirm the strongest opportunity signals with current primary-source evidence before acting.",
                related_symbols=strong[:3],
            )
        )
    if not recommendations:
        recommendations.append(
            PortfolioAutonomousRecommendation(
                category="monitoring",
                priority="low",
                title="Continue portfolio monitoring",
                explanation="No major autonomous portfolio rule was triggered. Continue tracking allocations, events, and research confidence.",
                related_symbols=[item.symbol for item in ranked[:3]],
            )
        )
    return recommendations
