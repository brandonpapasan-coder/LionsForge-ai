from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.knowledge_memory_remediation import (
    _action_key,
    _owned_context,
    _plan,
)
from app.db.session import get_db
from app.models.evidence import ResearchReviewAction, ResearchReviewActionHistory
from app.models.user import User
from app.schemas.knowledge_memory import (
    KnowledgeMemoryEvidenceRemediationActionVerification,
    KnowledgeMemoryEvidenceRemediationCriterionVerification,
    KnowledgeMemoryEvidenceRemediationResolveRequest,
    KnowledgeMemoryEvidenceRemediationResolveResult,
    KnowledgeMemoryEvidenceRemediationVerification,
)

router = APIRouter()
_ACTION_TYPES = (
    "restore_evidence",
    "resolve_contradiction",
    "review_evidence",
    "add_direct_support",
    "improve_source_quality",
)
_PENDING_STATUSES = {"unverified", "needs_review", "needs-review", "pending"}
_SUPPORTING_STANCES = {"supports", "supporting"}
_CONTRADICTING_STANCES = {"contradicts", "contradicting", "opposes"}


def _criterion(
    criterion: str,
    passed: bool,
    explanation: str,
    evidence_ids: list[int] | None = None,
) -> KnowledgeMemoryEvidenceRemediationCriterionVerification:
    return KnowledgeMemoryEvidenceRemediationCriterionVerification(
        criterion=criterion,
        passed=passed,
        explanation=explanation,
        supporting_evidence_ids=sorted(set(evidence_ids or [])),
    )


def _criteria_for(
    action_type: str,
    memory,
    records,
    unavailable_ids: list[int],
) -> list[KnowledgeMemoryEvidenceRemediationCriterionVerification]:
    supporting = [item for item in records if item.stance in _SUPPORTING_STANCES]
    contradicting = [item for item in records if item.stance in _CONTRADICTING_STANCES]
    pending = [item for item in records if item.validation_status in _PENDING_STATUSES]
    low_quality = [
        item
        for item in records
        if min(item.credibility_score, item.freshness_score, item.confidence_score) < 0.55
    ]

    if action_type == "restore_evidence":
        restored = not unavailable_ids
        return [
            _criterion(
                "Every unavailable evidence ID is restored or replaced.",
                restored,
                "All linked evidence IDs are owner-accessible."
                if restored
                else f"Unavailable evidence IDs remain: {sorted(unavailable_ids)}.",
                [item.id for item in records],
            ),
            _criterion(
                "The saved record evidence trace contains no unexplained inaccessible links.",
                restored,
                "The evidence trace contains no inaccessible links."
                if restored
                else "The evidence trace still contains inaccessible links.",
                [item.id for item in records],
            ),
        ]

    if action_type == "resolve_contradiction":
        no_active_conflict = not (supporting and contradicting)
        resolution_note = str((memory.provenance or {}).get("contradiction_resolution", "")).strip()
        record_reflects_resolution = memory.status != "contested" and bool(resolution_note)
        return [
            _criterion(
                "The contradiction is explicitly documented.",
                bool(resolution_note),
                "A contradiction resolution is recorded in saved-record provenance."
                if resolution_note
                else "No contradiction_resolution note is recorded in saved-record provenance.",
                [item.id for item in supporting + contradicting],
            ),
            _criterion(
                "The record statement or status reflects the resolved interpretation.",
                no_active_conflict and record_reflects_resolution,
                "The active evidence no longer conflicts and the record status reflects the documented resolution."
                if no_active_conflict and record_reflects_resolution
                else "Supporting and contradicting evidence still coexist, or the record remains contested without a documented resolution.",
                [item.id for item in supporting + contradicting],
            ),
        ]

    if action_type == "review_evidence":
        related = [item for item in records if item.validation_status not in {"rejected"}]
        final_statuses = not pending
        notes_complete = bool(related) and all((item.reviewer_notes or "").strip() for item in related)
        return [
            _criterion(
                "Every related evidence item has a non-pending validation status.",
                final_statuses,
                "Every linked evidence item has a final validation status."
                if final_statuses
                else f"Pending evidence IDs remain: {[item.id for item in pending]}.",
                [item.id for item in related],
            ),
            _criterion(
                "Reviewer notes explain each validation decision.",
                notes_complete,
                "Reviewer notes are present for every reviewed evidence item."
                if notes_complete
                else "One or more reviewed evidence items do not contain reviewer notes.",
                [item.id for item in related if (item.reviewer_notes or "").strip()],
            ),
        ]

    if action_type == "add_direct_support":
        approved_support = [
            item
            for item in supporting
            if item.validation_status in {"approved", "validated", "accepted"}
        ]
        direct_support = [item for item in approved_support if item.claim.strip() and item.excerpt.strip()]
        return [
            _criterion(
                "At least one linked evidence item has a supporting stance.",
                bool(supporting),
                "Supporting evidence is linked to the saved record."
                if supporting
                else "No linked evidence has a supporting stance.",
                [item.id for item in supporting],
            ),
            _criterion(
                "The supporting source directly addresses the saved record statement.",
                bool(direct_support),
                "At least one validated supporting source contains both a claim and excerpt."
                if direct_support
                else "No validated supporting source contains sufficient claim and excerpt detail.",
                [item.id for item in direct_support],
            ),
        ]

    if action_type == "improve_source_quality":
        justification = str((memory.provenance or {}).get("low_quality_evidence_justification", "")).strip()
        all_addressed = not low_quality or bool(justification)
        averages = []
        if records:
            averages = [
                sum(item.credibility_score for item in records) / len(records),
                sum(item.freshness_score for item in records) / len(records),
                sum(item.confidence_score for item in records) / len(records),
            ]
        adequate = bool(averages) and min(averages) >= 0.65
        return [
            _criterion(
                "Each related evidence item is replaced, supplemented, or explicitly justified.",
                all_addressed,
                "No low-quality evidence remains, or an explicit justification is recorded."
                if all_addressed
                else f"Low-quality evidence IDs remain without justification: {[item.id for item in low_quality]}.",
                [item.id for item in records if item not in low_quality],
            ),
            _criterion(
                "The record evidence-health averages meet the adequate threshold.",
                adequate,
                "Credibility, freshness, and confidence averages are each at least 0.65."
                if adequate
                else "One or more evidence-health averages remain below 0.65.",
                [item.id for item in records],
            ),
        ]

    raise HTTPException(status_code=422, detail="Unsupported remediation action type")


def _verification(db: Session, owner_id: int, memory_id: int) -> KnowledgeMemoryEvidenceRemediationVerification:
    memory, _, records, unavailable_ids = _owned_context(db, owner_id, memory_id)
    current_plan = _plan(db, owner_id, memory_id)
    current_by_type = {item.action_type: item for item in current_plan.actions}
    action_keys = [_action_key(memory_id, action_type) for action_type in _ACTION_TYPES]
    follow_ups = list(
        db.scalars(
            select(ResearchReviewAction).where(
                ResearchReviewAction.owner_id == owner_id,
                ResearchReviewAction.action_key.in_(action_keys),
                ResearchReviewAction.status != "dismissed",
            )
        ).all()
    )
    follow_up_by_key = {item.action_key: item for item in follow_ups}

    action_types = [
        action_type
        for action_type in _ACTION_TYPES
        if action_type in current_by_type or _action_key(memory_id, action_type) in follow_up_by_key
    ]
    actions = []
    for action_type in action_types:
        key = _action_key(memory_id, action_type)
        follow_up = follow_up_by_key.get(key)
        criteria = _criteria_for(action_type, memory, records, unavailable_ids)
        passed_count = sum(item.passed for item in criteria)
        status = (
            "ready_for_resolution"
            if passed_count == len(criteria)
            else "partially_satisfied"
            if passed_count
            else "unresolved"
        )
        actions.append(
            KnowledgeMemoryEvidenceRemediationActionVerification(
                action_key=key,
                action_type=action_type,
                follow_up_id=follow_up.id if follow_up else None,
                follow_up_status=follow_up.status if follow_up else None,
                status=status,
                passed_count=passed_count,
                total_count=len(criteria),
                criteria=criteria,
            )
        )

    return KnowledgeMemoryEvidenceRemediationVerification(
        memory_id=memory.id,
        project_id=memory.project_id,
        total_actions=len(actions),
        ready_for_resolution_count=sum(item.status == "ready_for_resolution" for item in actions),
        actions=actions,
    )


@router.get(
    "/{memory_id}/evidence-remediation/verification",
    response_model=KnowledgeMemoryEvidenceRemediationVerification,
)
def get_saved_record_evidence_remediation_verification(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceRemediationVerification:
    return _verification(db, current_user.id, memory_id)


@router.post(
    "/{memory_id}/evidence-remediation/verification/resolve",
    response_model=KnowledgeMemoryEvidenceRemediationResolveResult,
)
def resolve_verified_saved_record_evidence_remediation(
    memory_id: int,
    request: KnowledgeMemoryEvidenceRemediationResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceRemediationResolveResult:
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    verification = _verification(db, current_user.id, memory_id)
    action = next((item for item in verification.actions if item.action_key == request.action_key), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Remediation verification action not found")
    if action.status != "ready_for_resolution":
        raise HTTPException(status_code=409, detail="All completion criteria must pass before resolution")
    if action.follow_up_id is None:
        raise HTTPException(status_code=409, detail="Create the research follow-up before resolving it")
    follow_up = db.scalar(
        select(ResearchReviewAction).where(
            ResearchReviewAction.id == action.follow_up_id,
            ResearchReviewAction.owner_id == current_user.id,
        )
    )
    if follow_up is None:
        raise HTTPException(status_code=404, detail="Research follow-up not found")
    if follow_up.status == "resolved":
        if follow_up.resolved_at is None:
            raise HTTPException(status_code=409, detail="Resolved follow-up is missing its resolution timestamp")
        return KnowledgeMemoryEvidenceRemediationResolveResult(
            resolved=False,
            follow_up_id=follow_up.id,
            action_key=follow_up.action_key,
            status=follow_up.status,
            resolved_at=follow_up.resolved_at,
        )

    now = datetime.utcnow()
    previous = follow_up.status
    follow_up.status = "resolved"
    follow_up.resolution_notes = request.resolution_notes.strip()
    follow_up.resolved_at = now
    follow_up.updated_at = now
    db.add(
        ResearchReviewActionHistory(
            action_id=follow_up.id,
            owner_id=current_user.id,
            previous_status=previous,
            new_status="resolved",
            note=request.resolution_notes.strip(),
        )
    )
    db.commit()
    db.refresh(follow_up)
    return KnowledgeMemoryEvidenceRemediationResolveResult(
        resolved=True,
        follow_up_id=follow_up.id,
        action_key=follow_up.action_key,
        status=follow_up.status,
        resolved_at=follow_up.resolved_at,
    )
