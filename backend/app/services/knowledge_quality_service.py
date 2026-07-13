from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord
from app.models.knowledge_federation import KnowledgeFederationLink
from app.models.knowledge_memory import KnowledgeMemory, KnowledgeMemoryRevision
from app.models.mission import Mission
from app.models.research_planning import ResearchPlanRecommendation

METHODOLOGY_VERSION = "knowledge-quality-v1"
STALE_AFTER = timedelta(days=180)
RECENT_ACTIVITY_LIMIT = 20


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _count_by_status(records: list, statuses: tuple[str, ...]) -> dict[str, int]:
    counts = {status: 0 for status in statuses}
    for record in records:
        if record.status in counts:
            counts[record.status] += 1
    return counts


def build_knowledge_quality_dashboard(
    db: Session,
    owner_id: int,
    project_id: int | None = None,
) -> dict:
    memory_stmt = select(KnowledgeMemory).where(KnowledgeMemory.owner_id == owner_id)
    evidence_stmt = select(EvidenceRecord).where(EvidenceRecord.owner_id == owner_id)
    mission_stmt = select(Mission).where(Mission.owner_id == owner_id)
    planning_stmt = select(ResearchPlanRecommendation).where(
        ResearchPlanRecommendation.owner_id == owner_id
    )
    federation_stmt = select(KnowledgeFederationLink).where(
        KnowledgeFederationLink.owner_id == owner_id
    )
    if project_id is not None:
        memory_stmt = memory_stmt.where(KnowledgeMemory.project_id == project_id)
        evidence_stmt = evidence_stmt.where(EvidenceRecord.project_id == project_id)
        mission_stmt = mission_stmt.where(Mission.project_id == project_id)
        planning_stmt = planning_stmt.where(
            ResearchPlanRecommendation.project_id == project_id
        )
        federation_stmt = federation_stmt.where(
            or_(
                KnowledgeFederationLink.source_project_id == project_id,
                KnowledgeFederationLink.target_project_id == project_id,
            )
        )

    memories = list(db.scalars(memory_stmt).all())
    evidence = list(db.scalars(evidence_stmt).all())
    missions = list(db.scalars(mission_stmt).all())
    planning = list(db.scalars(planning_stmt).all())
    federation = list(db.scalars(federation_stmt).all())

    now = datetime.utcnow()
    stale_memories = [item for item in memories if now - item.updated_at > STALE_AFTER]
    memory_statuses = _count_by_status(
        memories,
        ("validated", "provisional", "contested", "superseded", "archived"),
    )
    mission_statuses = _count_by_status(
        missions,
        ("draft", "active", "blocked", "completed"),
    )
    planning_statuses = _count_by_status(
        planning,
        ("proposed", "accepted", "completed", "dismissed", "archived"),
    )

    confidences = [item.confidence for item in memories]
    average_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    median_confidence = round(float(median(confidences)), 4) if confidences else 0.0
    approved_evidence = sum(item.validation_status == "approved" for item in evidence)
    pending_evidence = sum(item.validation_status != "approved" for item in evidence)
    memories_with_evidence = sum(bool(item.source_evidence_ids) for item in memories)
    contradiction_links = [item for item in federation if item.link_type == "contradicting"]
    unresolved_contradictions = sum(item.status in {"proposed", "accepted"} for item in contradiction_links)
    active_memories = [item for item in memories if item.status not in {"superseded", "archived"}]
    federated_memory_ids = {
        memory_id
        for link in federation
        for memory_id in (link.source_memory_id, link.target_memory_id)
    }
    project_memory_ids = {item.id for item in memories}
    federated_project_memories = len(federated_memory_ids & project_memory_ids)

    revision_stmt = select(KnowledgeMemoryRevision).join(
        KnowledgeMemory,
        KnowledgeMemoryRevision.memory_id == KnowledgeMemory.id,
    ).where(KnowledgeMemory.owner_id == owner_id)
    if project_id is not None:
        revision_stmt = revision_stmt.where(KnowledgeMemory.project_id == project_id)
    revisions = list(db.scalars(revision_stmt).all())
    recent_revisions = sum(now - item.created_at <= timedelta(days=30) for item in revisions)

    evidence_coverage = _ratio(memories_with_evidence, len(memories))
    contradiction_rate = _ratio(len(contradiction_links), max(len(federation), 1))
    federation_coverage = _ratio(federated_project_memories, len(memories))
    freshness_score = 1.0 - _ratio(len(stale_memories), max(len(memories), 1))
    validation_score = _ratio(memory_statuses["validated"], max(len(active_memories), 1))
    confidence_score = average_confidence
    contradiction_score = 1.0 - _ratio(unresolved_contradictions, max(len(federation), 1))
    planning_score = 1.0 - _ratio(planning_statuses["proposed"], max(len(planning), 1))
    health_components = {
        "validation": round(validation_score, 4),
        "confidence": round(confidence_score, 4),
        "evidence_coverage": evidence_coverage,
        "freshness": round(freshness_score, 4),
        "contradiction_control": round(contradiction_score, 4),
        "planning_follow_through": round(planning_score, 4),
    }
    health_score = round(
        validation_score * 0.25
        + confidence_score * 0.2
        + evidence_coverage * 0.2
        + freshness_score * 0.15
        + contradiction_score * 0.1
        + planning_score * 0.1,
        4,
    )

    risks: list[dict] = []
    if memory_statuses["contested"]:
        risks.append(
            {
                "risk_type": "contested_knowledge",
                "severity": min(1.0, memory_statuses["contested"] / max(len(memories), 1)),
                "title": "Contested knowledge requires review",
                "detail": f"{memory_statuses['contested']} contested knowledge records remain visible.",
                "source_ids": [item.id for item in memories if item.status == "contested"][:10],
            }
        )
    if stale_memories:
        risks.append(
            {
                "risk_type": "stale_knowledge",
                "severity": min(1.0, len(stale_memories) / max(len(memories), 1)),
                "title": "Knowledge freshness risk",
                "detail": f"{len(stale_memories)} knowledge records exceed the 180-day review interval.",
                "source_ids": [item.id for item in stale_memories[:10]],
            }
        )
    if pending_evidence:
        risks.append(
            {
                "risk_type": "evidence_review_backlog",
                "severity": min(1.0, pending_evidence / max(len(evidence), 1)),
                "title": "Evidence review backlog",
                "detail": f"{pending_evidence} evidence records are not approved.",
                "source_ids": [item.id for item in evidence if item.validation_status != "approved"][:10],
            }
        )
    if unresolved_contradictions:
        risks.append(
            {
                "risk_type": "cross_project_contradiction",
                "severity": min(1.0, unresolved_contradictions / max(len(federation), 1)),
                "title": "Unresolved cross-project contradictions",
                "detail": f"{unresolved_contradictions} contradiction links remain unresolved.",
                "source_ids": [item.id for item in contradiction_links if item.status in {"proposed", "accepted"}][:10],
            }
        )
    risks.sort(key=lambda item: (-item["severity"], item["risk_type"]))

    priorities = sorted(
        [
            {
                "id": item.id,
                "project_id": item.project_id,
                "title": item.title,
                "status": item.status,
                "recommendation_type": item.recommendation_type,
                "priority_score": item.priority_score,
            }
            for item in planning
            if item.status in {"proposed", "accepted"}
        ],
        key=lambda item: (-item["priority_score"], -item["id"]),
    )[:10]

    activity = [
        {
            "record_type": "knowledge_memory",
            "record_id": item.id,
            "title": item.statement[:160],
            "status": item.status,
            "occurred_at": item.updated_at,
        }
        for item in memories
    ] + [
        {
            "record_type": "research_recommendation",
            "record_id": item.id,
            "title": item.title,
            "status": item.status,
            "occurred_at": item.updated_at,
        }
        for item in planning
    ]
    activity.sort(key=lambda item: item["occurred_at"], reverse=True)

    return {
        "project_id": project_id,
        "methodology_version": METHODOLOGY_VERSION,
        "generated_at": now,
        "health_score": health_score,
        "health_components": health_components,
        "memories": {
            "total": len(memories),
            **memory_statuses,
            "stale": len(stale_memories),
        },
        "evidence_total": len(evidence),
        "evidence_approved": approved_evidence,
        "evidence_pending_review": pending_evidence,
        "evidence_coverage_ratio": evidence_coverage,
        "average_confidence": average_confidence,
        "median_confidence": median_confidence,
        "contradiction_rate": contradiction_rate,
        "unresolved_contradictions": unresolved_contradictions,
        "federation_links": len(federation),
        "federation_coverage_ratio": federation_coverage,
        "missions": {"total": len(missions), **mission_statuses},
        "planning": {"total": len(planning), **planning_statuses},
        "knowledge_revision_velocity": recent_revisions,
        "review_backlog": pending_evidence + memory_statuses["contested"] + planning_statuses["proposed"],
        "top_risks": risks[:10],
        "top_priorities": priorities,
        "recent_activity": activity[:RECENT_ACTIVITY_LIMIT],
    }
