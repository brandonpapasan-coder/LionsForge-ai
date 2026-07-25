from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.investigation_evidence import (
    ClaimEvidence,
    ClaimValidationJudgment,
    InvestigationClaim,
)
from app.models.remediation_progress import RemediationProgress
from app.models.user import User
from app.schemas.review_queue import CrossInvestigationReviewQueue, ReviewQueueItem

router = APIRouter()

_PRIORITY = {
    "stale_validation": 5,
    "unresolved_contradiction": 5,
    "blocked_remediation": 5,
    "missing_validation": 4,
    "remediation_ready_for_review": 3,
}


def _item(
    *,
    investigation: Investigation,
    claim: InvestigationClaim,
    reason_type: str,
    reason: str,
    stored_inputs: list[str],
    latest_relevant_at: datetime,
    source_tables: list[str],
    source_record_ids: list[int],
) -> ReviewQueueItem:
    return ReviewQueueItem(
        item_key=f"{investigation.id}:{claim.id}:{reason_type}",
        investigation_id=investigation.id,
        investigation_title=investigation.title,
        investigation_status=investigation.status,
        claim_id=claim.id,
        claim_statement=claim.statement,
        reason_type=reason_type,
        workflow_priority=_PRIORITY[reason_type],
        reason=reason,
        stored_inputs=stored_inputs,
        latest_relevant_at=latest_relevant_at,
        source_tables=source_tables,
        source_record_ids=source_record_ids,
    )


@router.get("/review-queue", response_model=CrossInvestigationReviewQueue)
def cross_investigation_review_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CrossInvestigationReviewQueue:
    investigations = list(
        db.scalars(
            select(Investigation)
            .where(Investigation.owner_id == current_user.id)
            .order_by(Investigation.id)
        ).all()
    )
    investigation_by_id = {item.id: item for item in investigations}
    investigation_ids = list(investigation_by_id)
    if investigation_ids:
        claims = list(
            db.scalars(
                select(InvestigationClaim)
                .where(InvestigationClaim.investigation_id.in_(investigation_ids))
                .order_by(InvestigationClaim.id)
            ).all()
        )
    else:
        claims = []

    claim_ids = [claim.id for claim in claims]
    evidence_by_claim: dict[int, list[ClaimEvidence]] = {claim.id: [] for claim in claims}
    judgments_by_claim: dict[int, list[ClaimValidationJudgment]] = {
        claim.id: [] for claim in claims
    }
    progress_by_claim: dict[int, RemediationProgress] = {}

    if claim_ids:
        for evidence in db.scalars(
            select(ClaimEvidence).where(ClaimEvidence.claim_id.in_(claim_ids))
        ).all():
            evidence_by_claim[evidence.claim_id].append(evidence)
        for judgment in db.scalars(
            select(ClaimValidationJudgment).where(
                ClaimValidationJudgment.claim_id.in_(claim_ids),
                ClaimValidationJudgment.reviewer_id == current_user.id,
            )
        ).all():
            judgments_by_claim[judgment.claim_id].append(judgment)
        for progress in db.scalars(
            select(RemediationProgress).where(
                RemediationProgress.claim_id.in_(claim_ids),
                RemediationProgress.owner_id == current_user.id,
            )
        ).all():
            progress_by_claim[progress.claim_id] = progress

    items: list[ReviewQueueItem] = []
    for claim in claims:
        investigation = investigation_by_id[claim.investigation_id]
        evidence = evidence_by_claim[claim.id]
        judgments = sorted(
            judgments_by_claim[claim.id],
            key=lambda item: (item.reviewed_at, item.id),
            reverse=True,
        )
        latest_judgment = judgments[0] if judgments else None
        latest_evidence_update = max(
            (item.updated_at for item in evidence),
            default=None,
        )

        if latest_judgment is None:
            items.append(
                _item(
                    investigation=investigation,
                    claim=claim,
                    reason_type="missing_validation",
                    reason="No human validation judgment is stored for this claim.",
                    stored_inputs=["judgment_count=0"],
                    latest_relevant_at=max(
                        claim.updated_at,
                        latest_evidence_update or claim.updated_at,
                    ),
                    source_tables=["investigation_claims"],
                    source_record_ids=[claim.id],
                )
            )
        else:
            evidence_is_stale = latest_evidence_update is not None and (
                latest_judgment.evidence_updated_at_snapshot is None
                or latest_evidence_update
                > latest_judgment.evidence_updated_at_snapshot
            )
            claim_is_stale = (
                claim.updated_at > latest_judgment.claim_updated_at_snapshot
            )
            if claim_is_stale or evidence_is_stale:
                inputs = [
                    f"claim_updated_after_review={str(claim_is_stale).lower()}",
                    f"evidence_updated_after_review={str(evidence_is_stale).lower()}",
                ]
                items.append(
                    _item(
                        investigation=investigation,
                        claim=claim,
                        reason_type="stale_validation",
                        reason=(
                            "The latest human validation judgment predates a stored claim "
                            "or evidence update."
                        ),
                        stored_inputs=inputs,
                        latest_relevant_at=max(
                            claim.updated_at,
                            latest_evidence_update or claim.updated_at,
                        ),
                        source_tables=[
                            "investigation_claims",
                            "claim_validation_judgments",
                        ],
                        source_record_ids=[claim.id, latest_judgment.id],
                    )
                )

        contradicting = [
            item for item in evidence if item.relationship == "contradicts"
        ]
        if contradicting:
            items.append(
                _item(
                    investigation=investigation,
                    claim=claim,
                    reason_type="unresolved_contradiction",
                    reason="One or more stored evidence records contradict this claim.",
                    stored_inputs=[
                        f"contradicting_evidence_count={len(contradicting)}"
                    ],
                    latest_relevant_at=max(item.updated_at for item in contradicting),
                    source_tables=["claim_evidence"],
                    source_record_ids=sorted(item.id for item in contradicting),
                )
            )

        progress = progress_by_claim.get(claim.id)
        if progress is not None and progress.status in {
            "blocked",
            "ready_for_review",
        }:
            reason_type = (
                "blocked_remediation"
                if progress.status == "blocked"
                else "remediation_ready_for_review"
            )
            reason = (
                "Stored remediation progress is blocked."
                if progress.status == "blocked"
                else "Stored remediation progress is ready for human review."
            )
            items.append(
                _item(
                    investigation=investigation,
                    claim=claim,
                    reason_type=reason_type,
                    reason=reason,
                    stored_inputs=[f"remediation_status={progress.status}"],
                    latest_relevant_at=progress.updated_at,
                    source_tables=["remediation_progress"],
                    source_record_ids=[progress.id],
                )
            )

    deduplicated = {item.item_key: item for item in items}
    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (
            -item.workflow_priority,
            -item.latest_relevant_at.timestamp(),
            item.investigation_id,
            item.claim_id,
            item.reason_type,
        ),
    )
    return CrossInvestigationReviewQueue(
        status="active" if ordered else "empty",
        item_count=len(ordered),
        items=ordered,
    )
