from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.decision_intelligence import DecisionDriver, DecisionRecommendation
from app.services.event_intelligence_service import build_symbol_event_impact
from app.services.factor_service import get_factor_score
from app.services.market_providers import normalize_symbol
from app.services.research_agent_service import build_research_agent_report

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def build_decision_recommendation(symbol: str) -> DecisionRecommendation:
    normalized = normalize_symbol(symbol)
    factor = get_factor_score(normalized)
    research = build_research_agent_report(normalized)
    event_impact = build_symbol_event_impact(normalized)

    factor_opportunity = factor.composite_score
    research_confidence_percent = _confidence_percent(research.confidence_score)
    event_risk = _clamp(event_impact.impact_score)
    weak_factor_risk = _clamp(HUNDRED - factor.composite_score)
    risk_score = _clamp((event_risk * Decimal("0.60")) + (weak_factor_risk * Decimal("0.40")))
    opportunity_score = _clamp(
        (factor_opportunity * Decimal("0.70")) + (research_confidence_percent * Decimal("0.30"))
    )
    confidence_score = _clamp(
        (research_confidence_percent * Decimal("0.60"))
        + (Decimal("85") if normalized in {"AAPL", "MSFT", "NVDA", "TSLA"} else Decimal("60")) * Decimal("0.40")
    )

    action, priority = _decision_action(opportunity_score, risk_score, confidence_score)
    drivers = [
        DecisionDriver(
            source="factor",
            label="Composite factor score",
            score=factor.composite_score,
            direction="positive" if factor.composite_score >= Decimal("70") else "neutral" if factor.composite_score >= Decimal("50") else "negative",
            explanation=factor.explanation,
        ),
        DecisionDriver(
            source="research",
            label="Research confidence",
            score=research_confidence_percent,
            direction="positive" if research_confidence_percent >= Decimal("70") else "neutral",
            explanation=f"Research confidence is {research_confidence_percent} based on currently available evidence.",
        ),
        DecisionDriver(
            source="event",
            label="Event impact",
            score=event_risk,
            direction="negative" if event_risk >= Decimal("60") else "neutral",
            explanation=f"{event_impact.event_count} relevant events produce an impact score of {event_risk}.",
        ),
        DecisionDriver(
            source="risk",
            label="Weak-factor risk",
            score=weak_factor_risk,
            direction="negative" if weak_factor_risk >= Decimal("50") else "neutral",
            explanation="Risk contribution derived from the inverse of the composite factor score.",
        ),
    ]

    return DecisionRecommendation(
        symbol=normalized,
        action=action,
        priority=priority,
        opportunity_score=opportunity_score,
        risk_score=risk_score,
        confidence_score=confidence_score,
        rationale=_rationale(normalized, action, opportunity_score, risk_score, confidence_score),
        drivers=drivers,
        next_actions=_next_actions(action, event_impact.follow_up_actions, research.open_questions),
        limitations=[
            "This output supports research and is not financial advice or an execution instruction.",
            "Factor, event, and research inputs may include deterministic mock or fallback data.",
            "Primary filings, current fundamentals, valuation assumptions, and portfolio suitability require human review.",
        ],
        generated_at=datetime.now(timezone.utc),
    )


def _confidence_percent(value: Decimal) -> Decimal:
    return _clamp(value * HUNDRED if value <= Decimal("1") else value)


def _clamp(value: Decimal) -> Decimal:
    return max(ZERO, min(HUNDRED, value)).quantize(Decimal("0.000001"))


def _decision_action(opportunity: Decimal, risk: Decimal, confidence: Decimal) -> tuple[str, str]:
    if confidence < Decimal("50"):
        return "defer", "medium"
    if risk >= Decimal("65"):
        return "review_risk", "high"
    if opportunity >= Decimal("70") and risk < Decimal("50"):
        return "investigate", "high"
    return "monitor", "medium" if opportunity >= Decimal("50") else "low"


def _rationale(symbol: str, action: str, opportunity: Decimal, risk: Decimal, confidence: Decimal) -> str:
    return (
        f"{symbol} is classified as {action} with opportunity {opportunity}, risk {risk}, "
        f"and confidence {confidence}. The classification combines factor, research, and event evidence."
    )


def _next_actions(action: str, event_actions: list[str], research_questions: list[str]) -> list[str]:
    actions = list(event_actions[:2])
    actions.extend(f"Answer: {question}" for question in research_questions[:2])
    if action == "review_risk":
        actions.insert(0, "Review high-impact event and downside assumptions before further analysis.")
    elif action == "investigate":
        actions.insert(0, "Validate the strongest opportunity drivers with current primary-source evidence.")
    elif action == "defer":
        actions.insert(0, "Defer judgment until evidence quality and confidence improve.")
    else:
        actions.insert(0, "Continue monitoring material changes in factors, events, and evidence quality.")
    return actions
