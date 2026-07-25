from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.investigations import _owned_investigation
from app.db.session import get_db
from app.models.investigation_evidence import ClaimEvidence, ClaimValidationJudgment, InvestigationClaim
from app.models.remediation_progress import RemediationProgress, RemediationProgressHistory
from app.models.user import User
from app.schemas.investigation_provenance import (
    InvestigationProvenanceEvent,
    InvestigationProvenanceTimeline,
)

router = APIRouter()


def _changed(created_at: datetime, updated_at: datetime) -> bool:
    return updated_at > created_at


def _event(
    *,
    category: str,
    action: str,
    entity_type: str,
    entity_id: int,
    claim_id: int | None,
    claim_statement: str | None,
    authorship: str,
    summary: str,
    occurred_at: datetime,
    source_table: str,
) -> InvestigationProvenanceEvent:
    return InvestigationProvenanceEvent(
        event_key=f"{source_table}:{entity_id}:{action}",
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        claim_id=claim_id,
        claim_statement=claim_statement,
        authorship=authorship,
        summary=summary,
        occurred_at=occurred_at,
        source_table=source_table,
        source_record_id=entity_id,
    )


@router.get(
    "/{investigation_id}/provenance-timeline",
    response_model=InvestigationProvenanceTimeline,
)
def investigation_provenance_timeline(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationProvenanceTimeline:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    claim_by_id = {claim.id: claim for claim in claims}
    claim_ids = list(claim_by_id)
    events: list[InvestigationProvenanceEvent] = []

    for claim in claims:
        events.append(
            _event(
                category="claim",
                action="created",
                entity_type="investigation_claim",
                entity_id=claim.id,
                claim_id=claim.id,
                claim_statement=claim.statement,
                authorship="user_authored",
                summary="Claim created.",
                occurred_at=claim.created_at,
                source_table="investigation_claims",
            )
        )
        if _changed(claim.created_at, claim.updated_at):
            events.append(
                _event(
                    category="claim",
                    action="updated",
                    entity_type="investigation_claim",
                    entity_id=claim.id,
                    claim_id=claim.id,
                    claim_statement=claim.statement,
                    authorship="user_authored",
                    summary="Claim updated.",
                    occurred_at=claim.updated_at,
                    source_table="investigation_claims",
                )
            )

    if claim_ids:
        evidence_records = list(
            db.scalars(select(ClaimEvidence).where(ClaimEvidence.claim_id.in_(claim_ids))).all()
        )
        judgments = list(
            db.scalars(
                select(ClaimValidationJudgment).where(
                    ClaimValidationJudgment.claim_id.in_(claim_ids)
                )
            ).all()
        )
    else:
        evidence_records = []
        judgments = []

    for evidence in evidence_records:
        claim = claim_by_id[evidence.claim_id]
        summary = f'Evidence attached: "{evidence.source_title}" ({evidence.relationship}).'
        events.append(
            _event(
                category="evidence",
                action="created",
                entity_type="claim_evidence",
                entity_id=evidence.id,
                claim_id=claim.id,
                claim_statement=claim.statement,
                authorship="user_authored",
                summary=summary,
                occurred_at=evidence.created_at,
                source_table="claim_evidence",
            )
        )
        if _changed(evidence.created_at, evidence.updated_at):
            events.append(
                _event(
                    category="evidence",
                    action="updated",
                    entity_type="claim_evidence",
                    entity_id=evidence.id,
                    claim_id=claim.id,
                    claim_statement=claim.statement,
                    authorship="user_authored",
                    summary=f'Evidence updated: "{evidence.source_title}".',
                    occurred_at=evidence.updated_at,
                    source_table="claim_evidence",
                )
            )

    for judgment in judgments:
        claim = claim_by_id[judgment.claim_id]
        events.append(
            _event(
                category="validation",
                action="reviewed",
                entity_type="claim_validation_judgment",
                entity_id=judgment.id,
                claim_id=claim.id,
                claim_statement=claim.statement,
                authorship="human_judgment",
                summary=(
                    f"Human validation judgment recorded: {judgment.validation_status}; "
                    f"confidence {judgment.confidence_level}."
                ),
                occurred_at=judgment.reviewed_at,
                source_table="claim_validation_judgments",
            )
        )

    progress_records = list(
        db.scalars(
            select(RemediationProgress).where(
                RemediationProgress.investigation_id == investigation_id,
                RemediationProgress.owner_id == current_user.id,
            )
        ).all()
    )
    for progress in progress_records:
        claim = claim_by_id.get(progress.claim_id)
        events.append(
            _event(
                category="remediation_progress",
                action="created",
                entity_type="remediation_progress",
                entity_id=progress.id,
                claim_id=progress.claim_id,
                claim_statement=claim.statement if claim else None,
                authorship="user_authored",
                summary=f"Remediation progress created with status {progress.status}.",
                occurred_at=progress.created_at,
                source_table="remediation_progress",
            )
        )
        if _changed(progress.created_at, progress.updated_at):
            events.append(
                _event(
                    category="remediation_progress",
                    action="updated",
                    entity_type="remediation_progress",
                    entity_id=progress.id,
                    claim_id=progress.claim_id,
                    claim_statement=claim.statement if claim else None,
                    authorship="user_authored",
                    summary=f"Current remediation progress updated to {progress.status}.",
                    occurred_at=progress.updated_at,
                    source_table="remediation_progress",
                )
            )

    history_records = list(
        db.scalars(
            select(RemediationProgressHistory).where(
                RemediationProgressHistory.investigation_id == investigation_id,
                RemediationProgressHistory.owner_id == current_user.id,
            )
        ).all()
    )
    for history in history_records:
        claim = claim_by_id.get(history.claim_id)
        events.append(
            _event(
                category="remediation_history",
                action="recorded",
                entity_type="remediation_progress_history",
                entity_id=history.id,
                claim_id=history.claim_id,
                claim_statement=claim.statement if claim else None,
                authorship="user_authored",
                summary=f"Append-only remediation history recorded with status {history.status}.",
                occurred_at=history.recorded_at,
                source_table="remediation_progress_history",
            )
        )

    category_rank = {
        "remediation_history": 5,
        "remediation_progress": 4,
        "validation": 3,
        "evidence": 2,
        "claim": 1,
    }
    events.sort(
        key=lambda event: (
            event.occurred_at,
            category_rank[event.category],
            event.source_record_id,
            event.event_key,
        ),
        reverse=True,
    )
    return InvestigationProvenanceTimeline(
        investigation_id=investigation.id,
        title=investigation.title,
        status="active" if events else "empty",
        events=events,
    )
