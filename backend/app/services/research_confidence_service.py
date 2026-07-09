from decimal import Decimal

from app.schemas.evidence import EvidenceCollection
from app.schemas.research_confidence import ResearchConfidence
from app.services.evidence_service import collect_symbol_evidence


def calculate_research_confidence(symbol: str) -> ResearchConfidence:
    evidence = collect_symbol_evidence(symbol)
    return score_evidence_collection(evidence)


def score_evidence_collection(evidence: EvidenceCollection) -> ResearchConfidence:
    if not evidence.items:
        return ResearchConfidence(
            symbol=evidence.symbol,
            item_count=0,
            confidence=Decimal("0"),
            explanation="No evidence is available yet.",
        )

    total = sum(item.confidence for item in evidence.items)
    average = total / Decimal(len(evidence.items))
    return ResearchConfidence(
        symbol=evidence.symbol,
        item_count=len(evidence.items),
        confidence=average,
        explanation="Confidence is based on the average confidence of collected evidence items.",
    )
