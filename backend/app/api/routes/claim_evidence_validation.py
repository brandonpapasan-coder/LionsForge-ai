from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.investigation_evidence import ClaimEvidence, ClaimValidationJudgment, InvestigationClaim
from app.models.user import User
from app.schemas.investigation_report import (
    ClaimEvidenceValidationMap,
    ValidationMapClaim,
    ValidationMapEvidenceLink,
    ValidationMapHumanReview,
)

router = APIRouter()

_RELATIONSHIP_MAP = {
    "supports": "supporting",
    "contradicts": "contradicting",
    "neutral": "contextual",
}


def _owned_investigation(db: Session, user_id: int, investigation_id: int) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.owner_id == user_id,
        )
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


def _claim_status(counts: dict[str, int]) -> tuple[str, str]:
    if counts["contradicting"] > 0:
        return (
            "contested",
            "At least one recorded evidence item contradicts the claim, so contradiction takes precedence over support.",
        )
    if counts["supporting"] > 0:
        return (
            "supported",
            "One or more recorded evidence items support the claim and none contradict it.",
        )
    if counts["contextual"] > 0:
        return (
            "insufficient",
            "Recorded evidence is contextual only and does not directly support or contradict the claim.",
        )
    return (
        "unreviewed",
        "No evidence is attached, so the claim cannot be classified from recorded evidence.",
    )


def _human_review(
    claim: InvestigationClaim,
    evidence: list[ClaimEvidence],
    judgment: ClaimValidationJudgment | None,
) -> ValidationMapHumanReview:
    if judgment is None:
        return ValidationMapHumanReview(
            status="not_reviewed",
            validation_status=None,
            confidence_level=None,
            rationale=None,
            unresolved_questions=None,
            reviewed_at=None,
        )
    latest_evidence_update = max((item.updated_at for item in evidence), default=None)
    stale = claim.updated_at > judgment.claim_updated_at_snapshot or (
        latest_evidence_update is not None
        and (
            judgment.evidence_updated_at_snapshot is None
            or latest_evidence_update > judgment.evidence_updated_at_snapshot
        )
    )
    return ValidationMapHumanReview(
        status="stale" if stale else "current",
        validation_status=judgment.validation_status,
        confidence_level=judgment.confidence_level,
        rationale=judgment.rationale,
        unresolved_questions=judgment.unresolved_questions,
        reviewed_at=judgment.reviewed_at,
    )


def _missing_requirements(counts: dict[str, int]) -> list[str]:
    requirements: list[str] = []
    if sum(counts.values()) == 0:
        requirements.append("Attach at least one source-backed evidence item that directly tests the claim.")
    elif counts["supporting"] == 0:
        requirements.append("Add direct supporting evidence or revise the claim to match what the evidence establishes.")
    if counts["contradicting"] > 0:
        requirements.append("Resolve or explicitly explain the recorded contradicting evidence before treating the claim as settled.")
    if counts["supporting"] + counts["contradicting"] == 0 and counts["contextual"] > 0:
        requirements.append("Add evidence with a direct supporting or contradicting relationship; contextual evidence alone is insufficient.")
    return requirements


@router.get(
    "/{investigation_id}/validation-map",
    response_model=ClaimEvidenceValidationMap,
)
def validation_map(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidenceValidationMap:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    mapped_claims: list[ValidationMapClaim] = []
    summary = {"supported": 0, "contested": 0, "insufficient": 0, "unreviewed": 0}
    investigation_gaps: list[str] = []
    latest_state: datetime = investigation.updated_at

    for sequence, claim in enumerate(claims, start=1):
        evidence = list(
            db.scalars(
                select(ClaimEvidence)
                .where(ClaimEvidence.claim_id == claim.id)
                .order_by(ClaimEvidence.id)
            ).all()
        )
        judgment = db.scalar(
            select(ClaimValidationJudgment)
            .where(ClaimValidationJudgment.claim_id == claim.id)
            .order_by(ClaimValidationJudgment.reviewed_at.desc(), ClaimValidationJudgment.id.desc())
            .limit(1)
        )
        links: list[ValidationMapEvidenceLink] = []
        counts = {"supporting": 0, "contradicting": 0, "contextual": 0}
        confidence_inputs: list[str] = []

        if claim.confidence_level:
            confidence_inputs.append(f"Claim confidence recorded as {claim.confidence_level}.")
        else:
            confidence_inputs.append("No claim confidence assessment is recorded.")

        for item in evidence:
            relationship = _RELATIONSHIP_MAP[item.relationship]
            counts[relationship] += 1
            links.append(
                ValidationMapEvidenceLink(
                    evidence_id=item.id,
                    source_title=item.source_title,
                    source_url=item.source_url,
                    evidence_type=item.evidence_type,
                    relationship=relationship,
                    stored_relationship=item.relationship,
                    classification_rule=(
                        f"Stored relationship '{item.relationship}' maps directly to '{relationship}'."
                    ),
                    credibility_rating=item.credibility_rating,
                    credibility_rationale=item.credibility_rationale,
                    notes=item.notes,
                )
            )
            confidence_inputs.append(
                f"Evidence {item.id} credibility is {item.credibility_rating or 'not assessed'}."
            )
            latest_state = max(latest_state, item.updated_at)

        status, status_rule = _claim_status(counts)
        summary[status] += 1
        review = _human_review(claim, evidence, judgment)
        requirements = _missing_requirements(counts)
        gaps = list(requirements)
        if review.status == "not_reviewed":
            gaps.append("Record a human validation judgment after reviewing the current claim and evidence.")
        elif review.status == "stale":
            gaps.append("Refresh the human validation judgment because the claim or evidence changed after review.")
        if review.unresolved_questions:
            gaps.append(review.unresolved_questions)
        investigation_gaps.extend(f"Claim {claim.id}: {gap}" for gap in gaps)
        latest_state = max(latest_state, claim.updated_at)
        if judgment is not None:
            latest_state = max(latest_state, judgment.reviewed_at)

        mapped_claims.append(
            ValidationMapClaim(
                claim_id=claim.id,
                sequence=sequence,
                statement=claim.statement,
                status=status,
                status_rule=status_rule,
                relationship_counts=counts,
                confidence_inputs=confidence_inputs,
                evidence_links=links,
                missing_evidence_requirements=requirements,
                unresolved_gaps=gaps,
                human_review=review,
            )
        )

    if not claims:
        investigation_gaps.append("No material claims are recorded for this investigation.")

    return ClaimEvidenceValidationMap(
        investigation_id=investigation.id,
        title=investigation.title,
        status="active" if claims else "empty",
        claims=mapped_claims,
        summary_counts=summary,
        unresolved_gaps=investigation_gaps,
        generated_from_stored_state_at=latest_state,
    )