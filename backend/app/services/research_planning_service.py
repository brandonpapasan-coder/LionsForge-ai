import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_federation import KnowledgeFederationLink
from app.models.knowledge_memory import KnowledgeMemory
from app.models.research_planning import ResearchPlanRecommendation, ResearchPlanRevision

METHODOLOGY_VERSION = "research-planning-v1"
STALE_AFTER = timedelta(days=180)


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _priority(
    impact: float,
    urgency: float,
    confidence_deficit: float,
    contradiction_severity: float,
    freshness_risk: float,
    evidence_gap: float,
) -> tuple[float, dict]:
    components = {
        "impact": round(impact, 4),
        "urgency": round(urgency, 4),
        "confidence_deficit": round(confidence_deficit, 4),
        "contradiction_severity": round(contradiction_severity, 4),
        "freshness_risk": round(freshness_risk, 4),
        "evidence_gap": round(evidence_gap, 4),
    }
    score = round(
        impact * 0.25
        + urgency * 0.2
        + confidence_deficit * 0.2
        + contradiction_severity * 0.15
        + freshness_risk * 0.1
        + evidence_gap * 0.1,
        4,
    )
    return score, components


def _revision(item: ResearchPlanRecommendation) -> ResearchPlanRevision:
    return ResearchPlanRevision(
        recommendation_id=item.id,
        revision_number=item.revision_number,
        recommendation_type=item.recommendation_type,
        title=item.title,
        rationale=item.rationale,
        recommended_action=item.recommended_action,
        priority_score=item.priority_score,
        priority_components=item.priority_components,
        status=item.status,
        mission_id=item.mission_id,
        provenance=item.provenance,
    )


def generate_project_recommendations(
    db: Session,
    owner_id: int,
    project_id: int,
) -> tuple[list[ResearchPlanRecommendation], int, int]:
    memories = list(
        db.scalars(
            select(KnowledgeMemory).where(
                KnowledgeMemory.owner_id == owner_id,
                KnowledgeMemory.project_id == project_id,
            )
        ).all()
    )
    links = list(
        db.scalars(
            select(KnowledgeFederationLink).where(
                KnowledgeFederationLink.owner_id == owner_id,
                or_(
                    KnowledgeFederationLink.source_project_id == project_id,
                    KnowledgeFederationLink.target_project_id == project_id,
                ),
            )
        ).all()
    )
    candidates: list[dict] = []

    for memory in memories:
        confidence_deficit = max(0.0, 1.0 - memory.confidence)
        if memory.status == "contested":
            score, components = _priority(0.9, 0.85, confidence_deficit, 1.0, 0.2, 0.5)
            candidates.append(
                {
                    "recommendation_type": "contradiction_resolution",
                    "title": f"Resolve contested finding: {memory.statement[:120]}",
                    "rationale": "This knowledge memory is contested and may materially affect project conclusions.",
                    "recommended_action": "Collect independent evidence, compare competing claims, and document the resolution criteria.",
                    "priority_score": score,
                    "priority_components": components,
                    "source_memory_ids": [memory.id],
                    "source_evidence_ids": memory.source_evidence_ids,
                    "source_federation_link_ids": [],
                }
            )
        elif memory.status == "provisional" or memory.confidence < 0.7:
            score, components = _priority(0.75, 0.6, confidence_deficit, 0.2, 0.2, 0.7)
            candidates.append(
                {
                    "recommendation_type": "confidence_improvement",
                    "title": f"Strengthen confidence in: {memory.statement[:130]}",
                    "rationale": "The current conclusion is provisional or below the preferred confidence threshold.",
                    "recommended_action": "Add higher-quality primary evidence and repeat validation before promoting the conclusion.",
                    "priority_score": score,
                    "priority_components": components,
                    "source_memory_ids": [memory.id],
                    "source_evidence_ids": memory.source_evidence_ids,
                    "source_federation_link_ids": [],
                }
            )

        if datetime.utcnow() - memory.updated_at > STALE_AFTER:
            score, components = _priority(0.65, 0.7, confidence_deficit, 0.1, 1.0, 0.3)
            candidates.append(
                {
                    "recommendation_type": "freshness_review",
                    "title": f"Revalidate aging knowledge: {memory.statement[:125]}",
                    "rationale": "The knowledge record has exceeded the freshness review interval.",
                    "recommended_action": "Review recent evidence and confirm whether this conclusion remains current.",
                    "priority_score": score,
                    "priority_components": components,
                    "source_memory_ids": [memory.id],
                    "source_evidence_ids": memory.source_evidence_ids,
                    "source_federation_link_ids": [],
                }
            )

        for question in memory.provenance.get("unresolved_questions", []):
            score, components = _priority(0.8, 0.65, confidence_deficit, 0.25, 0.2, 0.9)
            candidates.append(
                {
                    "recommendation_type": "unanswered_question",
                    "title": f"Investigate unresolved question: {question[:130]}",
                    "rationale": "The final research snapshot explicitly recorded this question as unresolved.",
                    "recommended_action": "Create a focused research mission with evidence requirements tailored to this question.",
                    "priority_score": score,
                    "priority_components": components,
                    "source_memory_ids": [memory.id],
                    "source_evidence_ids": memory.source_evidence_ids,
                    "source_federation_link_ids": [],
                }
            )

    for link in links:
        if link.link_type == "contradicting":
            score, components = _priority(0.95, 0.9, 0.5, 1.0, 0.3, 0.6)
            candidates.append(
                {
                    "recommendation_type": "contradiction_resolution",
                    "title": "Resolve cross-project knowledge contradiction",
                    "rationale": "Federated knowledge contains a contradiction spanning multiple research projects.",
                    "recommended_action": "Compare source provenance, validate both claims, and define explicit supersession or coexistence criteria.",
                    "priority_score": score,
                    "priority_components": components,
                    "source_memory_ids": [link.source_memory_id, link.target_memory_id],
                    "source_evidence_ids": [],
                    "source_federation_link_ids": [link.id],
                }
            )

    if not links and memories:
        score, components = _priority(0.55, 0.4, 0.3, 0.0, 0.2, 0.65)
        candidates.append(
            {
                "recommendation_type": "federation_gap",
                "title": "Expand cross-project knowledge coverage",
                "rationale": "This project has durable knowledge but no identified federation links.",
                "recommended_action": "Scan related projects and validate whether comparable findings or shared themes exist.",
                "priority_score": score,
                "priority_components": components,
                "source_memory_ids": [memory.id for memory in memories],
                "source_evidence_ids": [],
                "source_federation_link_ids": [],
            }
        )

    created = 0
    reused = 0
    recommendations: list[ResearchPlanRecommendation] = []
    for candidate in candidates:
        provenance = {
            "project_id": project_id,
            "methodology_version": METHODOLOGY_VERSION,
            "generated_from": {
                "memory_ids": candidate["source_memory_ids"],
                "federation_link_ids": candidate["source_federation_link_ids"],
            },
        }
        fingerprint = _fingerprint(
            {
                "project_id": project_id,
                "type": candidate["recommendation_type"],
                "title": candidate["title"],
                "source_memory_ids": sorted(candidate["source_memory_ids"]),
                "source_federation_link_ids": sorted(candidate["source_federation_link_ids"]),
                "methodology": METHODOLOGY_VERSION,
            }
        )
        existing = db.scalar(
            select(ResearchPlanRecommendation).where(
                ResearchPlanRecommendation.owner_id == owner_id,
                ResearchPlanRecommendation.fingerprint == fingerprint,
            )
        )
        if existing is not None:
            recommendations.append(existing)
            reused += 1
            continue
        item = ResearchPlanRecommendation(
            owner_id=owner_id,
            project_id=project_id,
            provenance=provenance,
            fingerprint=fingerprint,
            **candidate,
        )
        db.add(item)
        db.flush()
        db.add(_revision(item))
        recommendations.append(item)
        created += 1
    db.commit()
    recommendations.sort(key=lambda item: (-item.priority_score, -item.id))
    return recommendations, created, reused


def list_recommendations(
    db: Session,
    owner_id: int,
    project_id: int | None = None,
    recommendation_type: str | None = None,
    status: str | None = None,
) -> list[ResearchPlanRecommendation]:
    stmt = select(ResearchPlanRecommendation).where(
        ResearchPlanRecommendation.owner_id == owner_id
    )
    if project_id is not None:
        stmt = stmt.where(ResearchPlanRecommendation.project_id == project_id)
    if recommendation_type is not None:
        stmt = stmt.where(
            ResearchPlanRecommendation.recommendation_type == recommendation_type
        )
    if status is not None:
        stmt = stmt.where(ResearchPlanRecommendation.status == status)
    return list(
        db.scalars(
            stmt.order_by(
                desc(ResearchPlanRecommendation.priority_score),
                desc(ResearchPlanRecommendation.id),
            )
        ).all()
    )
