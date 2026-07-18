from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.knowledge_memory import KnowledgeMemory
from app.models.user import User
from app.schemas.knowledge_memory import (
    EvidenceHealthClassification,
    KnowledgeMemoryEvidenceHealth,
    KnowledgeMemoryEvidenceHealthInventory,
    KnowledgeMemoryEvidenceHealthInventoryItem,
    KnowledgeMemoryEvidenceTrace,
)

router = APIRouter()

_APPROVED_STATUSES = {"approved", "validated"}
_NEEDS_REVIEW_STATUSES = {"unverified", "needs_review", "needs-review", "pending"}
_SUPPORTING_STANCES = {"supports", "supporting"}
_CONTRADICTING_STANCES = {"contradicts", "contradicting", "opposes"}
_HEALTH_PRIORITY = {
    "contested": 0,
    "unavailable": 1,
    "unsupported": 2,
    "weak": 3,
    "adequate": 4,
    "strong": 5,
}


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _assess_evidence_health(
    requested_ids: list[int],
    records: list[EvidenceRecord],
    unavailable_ids: list[int],
) -> KnowledgeMemoryEvidenceHealth:
    total_count = len(requested_ids)
    available_count = len(records)
    unavailable_count = len(unavailable_ids)
    approved_count = sum(record.validation_status in _APPROVED_STATUSES for record in records)
    needs_review_count = sum(record.validation_status in _NEEDS_REVIEW_STATUSES for record in records)
    supporting_count = sum(record.stance in _SUPPORTING_STANCES for record in records)
    contradicting_count = sum(record.stance in _CONTRADICTING_STANCES for record in records)
    average_credibility = _average([record.credibility_score for record in records])
    average_freshness = _average([record.freshness_score for record in records])
    average_confidence = _average([record.confidence_score for record in records])

    reasons: list[str] = []
    recommended_actions: list[str] = []

    if total_count == 0:
        classification = "unsupported"
        reasons.append("This saved record has no linked evidence.")
        recommended_actions.append("Link at least one relevant source before relying on this record.")
    elif available_count == 0:
        classification = "unavailable"
        reasons.append("None of the linked evidence is available to the current owner.")
        recommended_actions.append("Restore access or replace the unavailable evidence links.")
    elif contradicting_count > 0 and supporting_count > 0:
        classification = "contested"
        reasons.append("The linked evidence contains both supporting and contradicting claims.")
        recommended_actions.append("Review the contradiction and document why one interpretation is preferred.")
    else:
        score_values = [value for value in (average_credibility, average_freshness, average_confidence) if value is not None]
        composite_score = sum(score_values) / len(score_values) if score_values else 0.0
        approval_ratio = approved_count / available_count

        if unavailable_count == 0 and approval_ratio >= 0.75 and composite_score >= 0.75 and supporting_count > 0:
            classification = "strong"
            reasons.append("Most evidence is approved, available, supportive, and high quality.")
        elif approval_ratio >= 0.5 and composite_score >= 0.55 and supporting_count > 0:
            classification = "adequate"
            reasons.append("The evidence is usable but still has quality or review gaps.")
        else:
            classification = "weak"
            reasons.append("The evidence has limited approval, support, or quality scores.")

        if unavailable_count:
            reasons.append(f"{unavailable_count} linked evidence item(s) are unavailable.")
            recommended_actions.append("Replace or restore unavailable evidence.")
        if needs_review_count:
            reasons.append(f"{needs_review_count} evidence item(s) still need review.")
            recommended_actions.append("Review pending evidence and record validation decisions.")
        if supporting_count == 0:
            reasons.append("No available evidence explicitly supports this saved record.")
            recommended_actions.append("Add evidence that directly supports the saved record statement.")
        if composite_score < 0.55:
            recommended_actions.append("Add fresher, more credible, or higher-confidence sources.")

    return KnowledgeMemoryEvidenceHealth(
        classification=classification,
        total_count=total_count,
        available_count=available_count,
        unavailable_count=unavailable_count,
        approved_count=approved_count,
        needs_review_count=needs_review_count,
        supporting_count=supporting_count,
        contradicting_count=contradicting_count,
        average_credibility=average_credibility,
        average_freshness=average_freshness,
        average_confidence=average_confidence,
        reasons=reasons,
        recommended_actions=list(dict.fromkeys(recommended_actions)),
    )


@router.get("/evidence-health/inventory", response_model=KnowledgeMemoryEvidenceHealthInventory)
def get_knowledge_memory_evidence_health_inventory(
    project_id: int | None = Query(default=None),
    classification: EvidenceHealthClassification | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceHealthInventory:
    statement = select(KnowledgeMemory).where(KnowledgeMemory.owner_id == current_user.id)
    if project_id is not None:
        statement = statement.where(KnowledgeMemory.project_id == project_id)
    memories = list(db.scalars(statement).all())

    all_evidence_ids = list(
        dict.fromkeys(
            evidence_id
            for memory in memories
            for evidence_id in memory.source_evidence_ids
        )
    )
    evidence_records = (
        list(
            db.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.id.in_(all_evidence_ids),
                    EvidenceRecord.owner_id == current_user.id,
                )
            ).all()
        )
        if all_evidence_ids
        else []
    )
    records_by_id = {record.id: record for record in evidence_records}

    items: list[KnowledgeMemoryEvidenceHealthInventoryItem] = []
    by_classification: dict[str, int] = {}
    for memory in memories:
        requested_ids = list(dict.fromkeys(memory.source_evidence_ids))
        records = [records_by_id[evidence_id] for evidence_id in requested_ids if evidence_id in records_by_id]
        unavailable_ids = [evidence_id for evidence_id in requested_ids if evidence_id not in records_by_id]
        health = _assess_evidence_health(requested_ids, records, unavailable_ids)
        by_classification[health.classification] = by_classification.get(health.classification, 0) + 1
        if classification is not None and health.classification != classification:
            continue
        items.append(
            KnowledgeMemoryEvidenceHealthInventoryItem(
                memory_id=memory.id,
                project_id=memory.project_id,
                summary=memory.summary,
                statement=memory.statement,
                category=memory.category,
                status=memory.status,
                confidence=memory.confidence,
                updated_at=memory.updated_at,
                health=health,
            )
        )

    items.sort(
        key=lambda item: (
            _HEALTH_PRIORITY[item.health.classification],
            item.health.average_confidence if item.health.average_confidence is not None else -1,
            -item.updated_at.timestamp(),
        )
    )
    return KnowledgeMemoryEvidenceHealthInventory(
        project_id=project_id,
        classification=classification,
        total_count=len(items),
        by_classification=dict(sorted(by_classification.items())),
        items=items,
    )


@router.get("/{memory_id}/evidence", response_model=KnowledgeMemoryEvidenceTrace)
def get_knowledge_memory_evidence(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceTrace:
    memory = db.scalar(
        select(KnowledgeMemory).where(
            KnowledgeMemory.id == memory_id,
            KnowledgeMemory.owner_id == current_user.id,
        )
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Knowledge memory not found")

    requested_ids = list(dict.fromkeys(memory.source_evidence_ids))
    if not requested_ids:
        return KnowledgeMemoryEvidenceTrace(
            memory_id=memory.id,
            requested_evidence_ids=[],
            evidence=[],
            unavailable_evidence_ids=[],
            health=_assess_evidence_health([], [], []),
        )

    records = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.id.in_(requested_ids),
                EvidenceRecord.owner_id == current_user.id,
            )
        ).all()
    )
    records_by_id = {record.id: record for record in records}
    ordered_records = [records_by_id[evidence_id] for evidence_id in requested_ids if evidence_id in records_by_id]
    unavailable_ids = [evidence_id for evidence_id in requested_ids if evidence_id not in records_by_id]

    return KnowledgeMemoryEvidenceTrace(
        memory_id=memory.id,
        requested_evidence_ids=requested_ids,
        evidence=ordered_records,
        unavailable_evidence_ids=unavailable_ids,
        health=_assess_evidence_health(requested_ids, ordered_records, unavailable_ids),
    )
