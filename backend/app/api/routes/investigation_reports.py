from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation, InvestigationSynthesis
from app.models.investigation_evidence import ClaimEvidence, ClaimValidationJudgment, InvestigationClaim
from app.models.user import User
from app.schemas.investigation_report import (
    InvestigationSynthesisRead,
    InvestigationSynthesisUpdate,
    InvestigationValidationReport,
    ReportClaim,
    ReportEvidence,
    ReportJudgment,
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


def _synthesis(db: Session, investigation_id: int) -> InvestigationSynthesis | None:
    return db.scalar(
        select(InvestigationSynthesis).where(
            InvestigationSynthesis.investigation_id == investigation_id
        )
    )


@router.get("/{investigation_id}/synthesis", response_model=InvestigationSynthesisRead | None)
def read_synthesis(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationSynthesis | None:
    _owned_investigation(db, current_user.id, investigation_id)
    return _synthesis(db, investigation_id)


@router.put("/{investigation_id}/synthesis", response_model=InvestigationSynthesisRead)
def upsert_synthesis(
    investigation_id: int,
    payload: InvestigationSynthesisUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationSynthesis:
    _owned_investigation(db, current_user.id, investigation_id)
    if payload.findings is None and payload.limitations is None and payload.unresolved_questions is None:
        raise HTTPException(status_code=422, detail="At least one synthesis section must contain text")
    synthesis = _synthesis(db, investigation_id)
    if synthesis is None:
        synthesis = InvestigationSynthesis(investigation_id=investigation_id)
        db.add(synthesis)
    synthesis.findings = payload.findings
    synthesis.limitations = payload.limitations
    synthesis.unresolved_questions = payload.unresolved_questions
    db.commit()
    db.refresh(synthesis)
    return synthesis


@router.get("/{investigation_id}/validation-report", response_model=InvestigationValidationReport)
def validation_report(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationValidationReport:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    synthesis = _synthesis(db, investigation_id)
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    report_claims: list[ReportClaim] = []
    aggregate = {"supports": 0, "contradicts": 0, "neutral": 0}
    unresolved: list[str] = []
    latest_state = investigation.updated_at

    for claim in claims:
        evidence = list(
            db.scalars(
                select(ClaimEvidence)
                .where(ClaimEvidence.claim_id == claim.id)
                .order_by(ClaimEvidence.id)
            ).all()
        )
        counts = {"supports": 0, "contradicts": 0, "neutral": 0}
        for item in evidence:
            counts[item.relationship] = counts.get(item.relationship, 0) + 1
            aggregate[item.relationship] = aggregate.get(item.relationship, 0) + 1
            latest_state = max(latest_state, item.updated_at)

        judgment = db.scalar(
            select(ClaimValidationJudgment)
            .where(ClaimValidationJudgment.claim_id == claim.id)
            .order_by(ClaimValidationJudgment.reviewed_at.desc(), ClaimValidationJudgment.id.desc())
            .limit(1)
        )
        latest_judgment = None
        if judgment is not None:
            latest_evidence_update = max((item.updated_at for item in evidence), default=None)
            stale = claim.updated_at > judgment.claim_updated_at_snapshot or (
                latest_evidence_update is not None
                and (
                    judgment.evidence_updated_at_snapshot is None
                    or latest_evidence_update > judgment.evidence_updated_at_snapshot
                )
            )
            latest_judgment = ReportJudgment(
                validation_status=judgment.validation_status,
                confidence_level=judgment.confidence_level,
                rationale=judgment.rationale,
                unresolved_questions=judgment.unresolved_questions,
                reviewed_at=judgment.reviewed_at,
                is_stale=stale,
            )
            latest_state = max(latest_state, judgment.reviewed_at)
            if judgment.unresolved_questions:
                unresolved.append(judgment.unresolved_questions)

        latest_state = max(latest_state, claim.updated_at)
        report_claims.append(
            ReportClaim(
                id=claim.id,
                statement=claim.statement,
                confidence_level=claim.confidence_level,
                confidence_rationale=claim.confidence_rationale,
                relationship_counts=counts,
                evidence=[
                    ReportEvidence(
                        id=item.id,
                        source_title=item.source_title,
                        source_url=item.source_url,
                        evidence_type=item.evidence_type,
                        relationship=item.relationship,
                        credibility_rating=item.credibility_rating,
                        credibility_rationale=item.credibility_rationale,
                        notes=item.notes,
                    )
                    for item in evidence
                ],
                latest_judgment=latest_judgment,
                has_unresolved_contradiction=counts.get("contradicts", 0) > 0,
            )
        )

    limitations = []
    if synthesis and synthesis.limitations:
        limitations.append(synthesis.limitations)
    if not claims:
        limitations.append("No claims have been recorded for this investigation.")
    if any(not claim.evidence for claim in report_claims):
        limitations.append("One or more claims have no attached evidence.")
    if any(claim.latest_judgment is None for claim in report_claims):
        limitations.append("One or more claims have no validation judgment.")
    if synthesis and synthesis.unresolved_questions:
        unresolved.append(synthesis.unresolved_questions)
    if synthesis is not None:
        latest_state = max(latest_state, synthesis.updated_at)

    return InvestigationValidationReport(
        investigation_id=investigation.id,
        title=investigation.title,
        research_question=investigation.research_question,
        investigation_status=investigation.status,
        synthesis=(InvestigationSynthesisRead.model_validate(synthesis) if synthesis else None),
        claims=report_claims,
        aggregate_relationship_counts=aggregate,
        limitations=limitations,
        unresolved_questions=unresolved,
        generated_from_stored_state_at=latest_state if isinstance(latest_state, datetime) else investigation.updated_at,
    )
