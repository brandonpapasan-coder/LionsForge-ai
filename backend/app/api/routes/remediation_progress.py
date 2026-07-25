from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.evidence_gap_remediation import remediation_plan
from app.db.session import get_db
from app.models.investigation_evidence import InvestigationClaim
from app.models.remediation_progress import RemediationProgress, RemediationProgressHistory
from app.models.user import User
from app.schemas.investigation_report import EvidenceGapRemediationAction
from app.schemas.remediation_progress import (
    ActionType,
    ProgressStatus,
    RemediationCurrentAction,
    RemediationProgressEntry,
    RemediationProgressHistory as RemediationProgressHistoryResponse,
    RemediationProgressHistoryEvent,
    RemediationProgressLedger,
    RemediationProgressUpdate,
)

router = APIRouter()


def _current_action(
    action: EvidenceGapRemediationAction,
    generated_at: datetime,
) -> RemediationCurrentAction:
    return RemediationCurrentAction(
        action_type=action.action_type,
        priority=action.priority,
        rationale=action.rationale,
        completion_criteria=action.completion_criteria,
        generated_from_stored_state_at=generated_at,
    )


def _stale_reasons(
    record: RemediationProgress,
    current_action: RemediationCurrentAction | None,
) -> list[str]:
    if current_action is None:
        return ["No current remediation action exists for this claim."]
    reasons: list[str] = []
    if record.action_type_snapshot != current_action.action_type:
        reasons.append(
            "The deterministic remediation action type changed after this progress record was saved."
        )
    if record.priority_snapshot != current_action.priority:
        reasons.append(
            "The deterministic remediation priority changed after this progress record was saved."
        )
    if record.plan_generated_at_snapshot != current_action.generated_from_stored_state_at:
        reasons.append(
            "The underlying claim, evidence, or human-review state changed after this progress "
            "record was saved."
        )
    return reasons


def _ledger(
    investigation_id: int,
    current_user: User,
    db: Session,
) -> RemediationProgressLedger:
    plan = remediation_plan(
        investigation_id=investigation_id,
        current_user=current_user,
        db=db,
    )
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    claim_context: dict[int, tuple[int | None, str]] = {
        claim.id: (sequence, claim.statement)
        for sequence, claim in enumerate(claims, start=1)
    }
    current_actions = {
        action.claim_id: _current_action(
            action,
            plan.generated_from_stored_state_at,
        )
        for action in plan.actions
    }
    records = list(
        db.scalars(
            select(RemediationProgress)
            .where(
                RemediationProgress.investigation_id == investigation_id,
                RemediationProgress.owner_id == current_user.id,
            )
            .order_by(RemediationProgress.claim_id, RemediationProgress.id)
        ).all()
    )
    entries: list[RemediationProgressEntry] = []
    for record in records:
        sequence, statement = claim_context.get(
            record.claim_id,
            (None, "Claim no longer available"),
        )
        current_action = current_actions.get(record.claim_id)
        stale_reasons = _stale_reasons(record, current_action)
        entries.append(
            RemediationProgressEntry(
                claim_id=record.claim_id,
                claim_sequence=sequence,
                statement=statement,
                status=cast(ProgressStatus, record.status),
                notes=record.notes,
                is_stale=bool(stale_reasons),
                stale_reasons=stale_reasons,
                action_type_snapshot=cast(ActionType, record.action_type_snapshot),
                priority_snapshot=record.priority_snapshot,
                plan_generated_at_snapshot=record.plan_generated_at_snapshot,
                current_action=current_action,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
    entries.sort(
        key=lambda entry: (
            entry.current_action.priority
            if entry.current_action is not None
            else entry.priority_snapshot,
            entry.claim_sequence if entry.claim_sequence is not None else 10**9,
            entry.claim_id,
        )
    )
    return RemediationProgressLedger(
        investigation_id=plan.investigation_id,
        title=plan.title,
        status="active" if entries else "empty",
        entries=entries,
    )


def _history(
    investigation_id: int,
    claim_id: int,
    current_user: User,
    db: Session,
) -> RemediationProgressHistoryResponse:
    remediation_plan(
        investigation_id=investigation_id,
        current_user=current_user,
        db=db,
    )
    records = list(
        db.scalars(
            select(RemediationProgressHistory)
            .where(
                RemediationProgressHistory.investigation_id == investigation_id,
                RemediationProgressHistory.claim_id == claim_id,
                RemediationProgressHistory.owner_id == current_user.id,
            )
            .order_by(
                RemediationProgressHistory.recorded_at.desc(),
                RemediationProgressHistory.id.desc(),
            )
        ).all()
    )
    events = [
        RemediationProgressHistoryEvent(
            event_id=record.id,
            claim_id=record.claim_id,
            status=cast(ProgressStatus, record.status),
            notes=record.notes,
            action_type_snapshot=cast(ActionType, record.action_type_snapshot),
            priority_snapshot=record.priority_snapshot,
            plan_generated_at_snapshot=record.plan_generated_at_snapshot,
            recorded_at=record.recorded_at,
        )
        for record in records
    ]
    return RemediationProgressHistoryResponse(
        investigation_id=investigation_id,
        claim_id=claim_id,
        status="active" if events else "empty",
        events=events,
    )


@router.get(
    "/{investigation_id}/remediation-progress",
    response_model=RemediationProgressLedger,
)
def get_remediation_progress(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemediationProgressLedger:
    return _ledger(investigation_id, current_user, db)


@router.get(
    "/{investigation_id}/remediation-progress/{claim_id}/history",
    response_model=RemediationProgressHistoryResponse,
)
def get_remediation_progress_history(
    investigation_id: int,
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemediationProgressHistoryResponse:
    return _history(investigation_id, claim_id, current_user, db)


@router.put(
    "/{investigation_id}/remediation-progress/{claim_id}",
    response_model=RemediationProgressLedger,
)
def put_remediation_progress(
    investigation_id: int,
    claim_id: int,
    payload: RemediationProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemediationProgressLedger:
    plan = remediation_plan(
        investigation_id=investigation_id,
        current_user=current_user,
        db=db,
    )
    action = next((item for item in plan.actions if item.claim_id == claim_id), None)
    if action is None:
        raise HTTPException(
            status_code=409,
            detail="A current remediation action is required before progress can be recorded.",
        )
    record = db.scalar(
        select(RemediationProgress).where(
            RemediationProgress.investigation_id == investigation_id,
            RemediationProgress.claim_id == claim_id,
            RemediationProgress.owner_id == current_user.id,
        )
    )
    if record is None:
        record = RemediationProgress(
            investigation_id=investigation_id,
            claim_id=claim_id,
            owner_id=current_user.id,
            status=payload.status,
            notes=payload.notes,
            action_type_snapshot=action.action_type,
            priority_snapshot=action.priority,
            plan_generated_at_snapshot=plan.generated_from_stored_state_at,
        )
        db.add(record)
        db.flush()
    else:
        record.status = payload.status
        record.notes = payload.notes
        record.action_type_snapshot = action.action_type
        record.priority_snapshot = action.priority
        record.plan_generated_at_snapshot = plan.generated_from_stored_state_at
    db.add(
        RemediationProgressHistory(
            progress_id=record.id,
            investigation_id=investigation_id,
            claim_id=claim_id,
            owner_id=current_user.id,
            status=payload.status,
            notes=payload.notes,
            action_type_snapshot=action.action_type,
            priority_snapshot=action.priority,
            plan_generated_at_snapshot=plan.generated_from_stored_state_at,
        )
    )
    db.commit()
    return _ledger(investigation_id, current_user, db)
