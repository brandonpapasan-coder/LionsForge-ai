from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.investigation_evidence import ClaimEvidence, InvestigationClaim
from app.models.user import User
from app.schemas.investigation import InvestigationRead, InvestigationSynthesisUpdate
from app.schemas.investigation_report import (
    InvestigationValidationReport,
    ReportClaim,
    ReportEvidence,
)

router = APIRouter()


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


@router.patch("/{investigation_id}/synthesis", response_model=InvestigationRead)
def update_synthesis(
    investigation_id: int,
    payload: InvestigationSynthesisUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Investigation:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one synthesis section must be updated")
    for field_name, value in changes.items():
        setattr(investigation, field_name, value)
    db.commit()
    db.refresh(investigation)
    return investigation


@router.get("/{investigation_id}/validation-report", response_model=InvestigationValidationReport)
def get_validation_report(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationValidationReport:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    report_claims: list[ReportClaim] = []
    for claim in claims:
        evidence = list(
            db.scalars(
                select(ClaimEvidence)
                .where(ClaimEvidence.claim_id == claim.id)
                .order_by(ClaimEvidence.id)
            ).all()
        )
        supporting_count = sum(item.relationship == "supports" for item in evidence)
        contradicting_count = sum(item.relationship == "contradicts" for item in evidence)
        neutral_count = sum(item.relationship == "neutral" for item in evidence)
        report_claims.append(
            ReportClaim(
                id=claim.id,
                statement=claim.statement,
                confidence_level=claim.confidence_level,
                confidence_rationale=claim.confidence_rationale,
                supporting_count=supporting_count,
                contradicting_count=contradicting_count,
                neutral_count=neutral_count,
                has_unresolved_contradiction=contradicting_count > 0,
                evidence=[
                    ReportEvidence(
                        id=item.id,
                        source_title=item.source_title,
                        source_url=item.source_url,
                        evidence_type=item.evidence_type,
                        relationship=item.relationship,
                        notes=item.notes,
                        credibility_rating=item.credibility_rating,
                        credibility_rationale=item.credibility_rationale,
                    )
                    for item in evidence
                ],
            )
        )
    return InvestigationValidationReport(
        investigation_id=investigation.id,
        title=investigation.title,
        research_question=investigation.research_question,
        status=investigation.status,
        findings=investigation.findings,
        limitations=investigation.limitations,
        unresolved_questions=investigation.unresolved_questions,
        generated_from_updated_at=investigation.updated_at,
        claim_count=len(report_claims),
        unresolved_contradiction_count=sum(
            claim.has_unresolved_contradiction for claim in report_claims
        ),
        claims=report_claims,
    )
