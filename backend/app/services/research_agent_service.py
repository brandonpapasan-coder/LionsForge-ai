from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.research_agent import ResearchAgentFinding, ResearchAgentReport
from app.services.factor_service import get_factor_score
from app.services.research_confidence_service import calculate_research_confidence
from app.services.research_context_service import build_research_context

COMPANY_SUMMARIES = {
    "AAPL": "Apple designs consumer devices, software, and digital services within a tightly integrated ecosystem.",
    "MSFT": "Microsoft develops enterprise software, cloud infrastructure, productivity applications, and AI services.",
    "NVDA": "NVIDIA develops accelerated computing platforms, graphics processors, networking products, and AI infrastructure.",
    "TSLA": "Tesla manufactures electric vehicles and develops energy storage, charging, and related software products.",
}


def build_research_agent_report(symbol: str) -> ResearchAgentReport:
    normalized = symbol.strip().upper()
    context = build_research_context(normalized)
    factor = get_factor_score(normalized)
    confidence = calculate_research_confidence(normalized)
    evidence = [f"Quote source: {context.quote.source}"] + [f"News: {item.title}" for item in context.news[:3]]
    confidence_score = Decimal(str(confidence.confidence)).quantize(Decimal("0.000001"))

    findings = [
        ResearchAgentFinding(
            category="strength",
            title="Composite factor profile",
            summary=f"The current deterministic factor model rates {normalized} as {factor.rating}.",
            evidence=[f"Composite factor score: {factor.composite_score}"],
            confidence=Decimal("0.800000"),
        ),
        ResearchAgentFinding(
            category="risk",
            title="Evidence limitations",
            summary="The current report uses deterministic mock factor inputs and delayed or fallback market context.",
            evidence=evidence,
            confidence=Decimal("0.950000"),
        ),
        ResearchAgentFinding(
            category="opportunity",
            title="Research follow-up",
            summary="Review the strongest factor contributors and validate them against current filings and financial statements.",
            evidence=[item.explanation for item in factor.factors if item.normalized_score >= Decimal("75")][:3],
            confidence=Decimal("0.700000"),
        ),
        ResearchAgentFinding(
            category="question",
            title="Open diligence question",
            summary="What new evidence would materially change the current factor rating or risk assessment?",
            evidence=[],
            confidence=Decimal("0.650000"),
        ),
    ]

    return ResearchAgentReport(
        symbol=normalized,
        business_summary=COMPANY_SUMMARIES.get(
            normalized,
            f"{normalized} requires a validated company profile from an external fundamentals provider.",
        ),
        market_context=f"Latest available quote is {context.quote.price} {context.quote.currency} from {context.quote.source}.",
        factor_score=factor.composite_score,
        factor_rating=factor.rating,
        confidence_score=confidence_score,
        freshness="mock" if context.quote.source == "mock-market-data" else "fresh",
        findings=findings,
        bull_case=f"A constructive case depends on sustained strength in the highest-scoring factors and confirming external evidence for {normalized}.",
        bear_case=f"A cautious case emphasizes weak factors, concentration in assumptions, stale data, and evidence gaps for {normalized}.",
        open_questions=[
            "Are the latest financial statements consistent with the factor profile?",
            "Have recent company events changed the risk or opportunity assessment?",
            "Which assumptions are most sensitive to new evidence?",
        ],
        limitations=[
            "This report is research support, not financial advice.",
            "Mock and fallback data may not reflect current market conditions.",
            "External filings and licensed fundamentals should be reviewed before decisions.",
        ],
        generated_at=datetime.now(timezone.utc),
    )
