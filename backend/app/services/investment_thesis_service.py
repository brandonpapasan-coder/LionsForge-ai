from app.schemas.investment_thesis import InvestmentThesis
from app.services.evidence_service import collect_symbol_evidence
from app.services.research_confidence_service import calculate_research_confidence


def build_investment_thesis(symbol: str) -> InvestmentThesis:
    normalized = symbol.strip().upper()
    evidence = collect_symbol_evidence(normalized)
    confidence = calculate_research_confidence(normalized)
    categories = {item.category for item in evidence.items}
    evidence_ids = [item.evidence_id for item in evidence.items]

    bull_case = []
    bear_case = []
    risks = []
    catalysts = []

    if "market_quote" in categories:
        bull_case.append("Market quote evidence is available for current price context.")
    if "company_news" in categories:
        catalysts.append("Recent company news evidence is available for review.")
    if confidence.confidence < 1:
        risks.append("Research confidence is limited by the quality and depth of available evidence.")
    if not bear_case:
        bear_case.append("No explicit bearish evidence has been identified in the current evidence set.")

    return InvestmentThesis(
        symbol=normalized,
        summary=f"Evidence-backed thesis draft for {normalized} based on current quote and news context.",
        bull_case=bull_case,
        bear_case=bear_case,
        risks=risks,
        catalysts=catalysts,
        confidence=confidence.confidence,
        evidence_count=len(evidence.items),
        supporting_evidence_ids=evidence_ids,
    )
