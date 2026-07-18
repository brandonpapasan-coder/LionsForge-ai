import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.knowledge_memory_evidence import _assess_evidence_health
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, ResearchReviewAction, ResearchReviewActionHistory
from app.models.knowledge_memory import KnowledgeMemory
from app.models.user import User
from app.schemas.knowledge_memory import (
    KnowledgeMemoryEvidenceRemediationAction,
    KnowledgeMemoryEvidenceRemediationCreateRequest,
    KnowledgeMemoryEvidenceRemediationCreateResult,
    KnowledgeMemoryEvidenceRemediationPlan,
)

router = APIRouter()
_TERMINAL_STATUSES = {"resolved", "dismissed"}


def _action_key(memory_id: int, action_type: str) -> str:
    digest = hashlib.sha256(f"memory:{memory_id}:{action_type}".encode()).hexdigest()[:24]
    return f"memory-remediation-{digest}"


def _owned_context(
    db: Session,
    owner_id: int,
    memory_id: int,
) -> tuple[KnowledgeMemory, list[int], list[EvidenceRecord], list[int]]:
    memory = db.scalar(
        select(KnowledgeMemory).where(
            KnowledgeMemory.id == memory_id,
            KnowledgeMemory.owner_id == owner_id,
        )
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Knowledge memory not found")
    requested_ids = list(dict.fromkeys(memory.source_evidence_ids))
    records = (
        list(
            db.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.id.in_(requested_ids),
                    EvidenceRecord.owner_id == owner_id,
                )
            ).all()
        )
        if requested_ids
        else []
    )
    records_by_id = {record.id: record for record in records}
    ordered_records = [records_by_id[item_id] for item_id in requested_ids if item_id in records_by_id]
    unavailable_ids = [item_id for item_id in requested_ids if item_id not in records_by_id]
    return memory, requested_ids, ordered_records, unavailable_ids


def _remediation_actions(
    memory: KnowledgeMemory,
    records: list[EvidenceRecord],
    unavailable_ids: list[int],
) -> list[KnowledgeMemoryEvidenceRemediationAction]:
    actions: list[KnowledgeMemoryEvidenceRemediationAction] = []
    needs_review_ids = [
        record.id
        for record in records
        if record.validation_status in {"unverified", "needs_review", "needs-review", "pending"}
    ]
    supporting_ids = [record.id for record in records if record.stance in {"supports", "supporting"}]
    contradicting_ids = [
        record.id
        for record in records
        if record.stance in {"contradicts", "contradicting", "opposes"}
    ]
    low_quality_ids = [
        record.id
        for record in records
        if min(record.credibility_score, record.freshness_score, record.confidence_score) < 0.55
    ]

    def add(
        action_type: str,
        priority: str,
        rationale: str,
        action_text: str,
        evidence_ids: list[int],
        completion_criteria: list[str],
    ) -> None:
        actions.append(
            KnowledgeMemoryEvidenceRemediationAction(
                action_key=_action_key(memory.id, action_type),
                action_type=action_type,
                priority=priority,
                rationale=rationale,
                action_text=action_text,
                related_evidence_ids=sorted(set(evidence_ids)),
                completion_criteria=completion_criteria,
            )
        )

    if unavailable_ids:
        add(
            "restore_evidence",
            "urgent" if len(unavailable_ids) == len(memory.source_evidence_ids) else "high",
            f"{len(unavailable_ids)} linked evidence item(s) are unavailable to the record owner.",
            "Restore access to the unavailable evidence or replace each link with an owner-accessible source.",
            unavailable_ids,
            [
                "Every unavailable evidence ID is restored or replaced.",
                "The saved record evidence trace contains no unexplained inaccessible links.",
            ],
        )
    if supporting_ids and contradicting_ids:
        add(
            "resolve_contradiction",
            "urgent",
            "The saved record has both supporting and contradicting evidence.",
            "Review the conflicting claims and document the preferred interpretation or revise the saved record.",
            supporting_ids + contradicting_ids,
            [
                "The contradiction is explicitly documented.",
                "The record statement or status reflects the resolved interpretation.",
            ],
        )
    if needs_review_ids:
        add(
            "review_evidence",
            "high",
            f"{len(needs_review_ids)} linked evidence item(s) still require validation review.",
            "Review each pending evidence item and record a validation decision with reviewer notes.",
            needs_review_ids,
            [
                "Every related evidence item has a non-pending validation status.",
                "Reviewer notes explain each validation decision.",
            ],
        )
    if not supporting_ids:
        add(
            "add_direct_support",
            "high" if records else "urgent",
            "No available linked evidence directly supports the saved record statement.",
            "Add at least one owner-accessible source that directly supports the saved record statement.",
            [],
            [
                "At least one linked evidence item has a supporting stance.",
                "The supporting source directly addresses the saved record statement.",
            ],
        )
    if low_quality_ids:
        add(
            "improve_source_quality",
            "normal",
            f"{len(low_quality_ids)} evidence item(s) have low credibility, freshness, or confidence.",
            "Replace or supplement low-quality evidence with fresher, more credible, higher-confidence sources.",
            low_quality_ids,
            [
                "Each related evidence item is replaced, supplemented, or explicitly justified.",
                "The record evidence-health averages meet the adequate threshold.",
            ],
        )
    return actions


def _plan(db: Session, owner_id: int, memory_id: int) -> KnowledgeMemoryEvidenceRemediationPlan:
    memory, requested_ids, records, unavailable_ids = _owned_context(db, owner_id, memory_id)
    health = _assess_evidence_health(requested_ids, records, unavailable_ids)
    actions = _remediation_actions(memory, records, unavailable_ids)
    action_keys = [action.action_key for action in actions]
    existing = (
        list(
            db.scalars(
                select(ResearchReviewAction).where(
                    ResearchReviewAction.owner_id == owner_id,
                    ResearchReviewAction.action_key.in_(action_keys),
                    ResearchReviewAction.status.notin_(_TERMINAL_STATUSES),
                )
            ).all()
        )
        if action_keys
        else []
    )
    existing_by_key = {item.action_key: item for item in existing}
    resolved_actions = [
        action.model_copy(
            update={
                "existing_follow_up_id": existing_by_key[action.action_key].id
                if action.action_key in existing_by_key
                else None
            }
        )
        for action in actions
    ]
    return KnowledgeMemoryEvidenceRemediationPlan(
        memory_id=memory.id,
        project_id=memory.project_id,
        health=health,
        total_actions=len(resolved_actions),
        open_follow_up_count=sum(action.existing_follow_up_id is not None for action in resolved_actions),
        actions=resolved_actions,
    )


def _refresh_follow_up(
    follow_up: ResearchReviewAction,
    action: KnowledgeMemoryEvidenceRemediationAction,
    memory_id: int,
    project_id: int,
) -> None:
    follow_up.project_id = project_id
    follow_up.evidence_id = action.related_evidence_ids[0] if action.related_evidence_ids else 0
    follow_up.impact_level = "high_attention" if action.priority in {"urgent", "high"} else "review_required"
    follow_up.governing_rule = f"saved_record_{action.action_type}"
    follow_up.reason = action.rationale
    follow_up.action_text = f"{action.action_text} Completion: {' '.join(action.completion_criteria)}"
    follow_up.supporting_event_ids = [f"memory:{memory_id}"] + [
        f"evidence:{item_id}" for item_id in action.related_evidence_ids
    ]
    follow_up.priority = action.priority


@router.get(
    "/{memory_id}/evidence-remediation",
    response_model=KnowledgeMemoryEvidenceRemediationPlan,
)
def get_saved_record_evidence_remediation(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceRemediationPlan:
    return _plan(db, current_user.id, memory_id)


@router.post(
    "/{memory_id}/evidence-remediation/follow-ups",
    response_model=KnowledgeMemoryEvidenceRemediationCreateResult,
)
def create_saved_record_evidence_follow_up(
    memory_id: int,
    request: KnowledgeMemoryEvidenceRemediationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceRemediationCreateResult:
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    plan = _plan(db, current_user.id, memory_id)
    action = next((item for item in plan.actions if item.action_key == request.action_key), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if action.existing_follow_up_id is not None:
        return KnowledgeMemoryEvidenceRemediationCreateResult(
            created=False,
            follow_up_id=action.existing_follow_up_id,
            action_key=action.action_key,
        )

    existing = db.scalar(
        select(ResearchReviewAction).where(
            ResearchReviewAction.owner_id == current_user.id,
            ResearchReviewAction.action_key == action.action_key,
        )
    )
    if existing is not None:
        previous_status = existing.status
        _refresh_follow_up(existing, action, memory_id, plan.project_id)
        existing.status = "open"
        existing.resolved_at = None
        existing.resolution_notes = None
        existing.updated_at = datetime.utcnow()
        db.add(
            ResearchReviewActionHistory(
                action_id=existing.id,
                owner_id=current_user.id,
                previous_status=previous_status,
                new_status="open",
                note="Reopened because the saved-record remediation condition remains active.",
            )
        )
        db.commit()
        db.refresh(existing)
        return KnowledgeMemoryEvidenceRemediationCreateResult(
            created=False,
            follow_up_id=existing.id,
            action_key=existing.action_key,
        )

    follow_up = ResearchReviewAction(
        owner_id=current_user.id,
        project_id=plan.project_id,
        evidence_id=action.related_evidence_ids[0] if action.related_evidence_ids else 0,
        action_key=action.action_key,
        impact_level="high_attention" if action.priority in {"urgent", "high"} else "review_required",
        governing_rule=f"saved_record_{action.action_type}",
        reason=action.rationale,
        action_text=f"{action.action_text} Completion: {' '.join(action.completion_criteria)}",
        supporting_event_ids=[f"memory:{memory_id}"] + [
            f"evidence:{item_id}" for item_id in action.related_evidence_ids
        ],
        status="open",
        priority=action.priority,
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return KnowledgeMemoryEvidenceRemediationCreateResult(
        created=True,
        follow_up_id=follow_up.id,
        action_key=follow_up.action_key,
    )
