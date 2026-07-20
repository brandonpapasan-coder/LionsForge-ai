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
    InvestigationQualityAssessment,
    InvestigationSynthesisRead,
    InvestigationSynthesisUpdate,
    InvestigationValidationReport,
    QualityAssessmentDimension,
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


def _dimension(
    key: str,
    label: str,
    status: str,
    counts: dict[str, int],
    explanation: str,
) -> QualityAssessmentDimension:
    return QualityAssessmentDimension(
        key=key,
        label=label,
        status=status,
        counts=counts,
        explanation=explanation,
    )


@router.get("/{investigation_id}/quality-assessment", response_model=InvestigationQualityAssessment)
def quality_assessment(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationQualityAssessment:
    report = validation_report(investigation_id, current_user, db)
    claim_count = len(report.claims)
    evidence_count = sum(len(claim.evidence) for claim in report.claims)
    claims_with_evidence = sum(bool(claim.evidence) for claim in report.claims)
    evidence_types = sorted({item.evidence_type for claim in report.claims for item in claim.evidence})
    judgments = [claim.latest_judgment for claim in report.claims if claim.latest_judgment is not None]
    current_judgments = sum(not judgment.is_stale for judgment in judgments)
    synthesis = report.synthesis

    if claim_count == 0:
        claim_status = "missing"
    else:
        claim_status = "complete"

    if evidence_count == 0:
        evidence_status = "missing"
    elif claims_with_evidence < claim_count:
        evidence_status = "partial"
    else:
        evidence_status = "complete"

    if not evidence_types:
        diversity_status = "missing"
    elif len(evidence_types) == 1:
        diversity_status = "partial"
    else:
        diversity_status = "complete"

    if not judgments:
        judgment_status = "missing"
    elif current_judgments < claim_count:
        judgment_status = "partial"
    else:
        judgment_status = "complete"

    synthesis_status = "complete" if synthesis and synthesis.findings else "missing"
    limitations_status = "complete" if synthesis and synthesis.limitations else "missing"
    unresolved_status = "complete" if synthesis and synthesis.unresolved_questions else "missing"

    dimensions = [
        _dimension(
            "claim_coverage",
            "Claim coverage",
            claim_status,
            {"claims": claim_count},
            "At least one explicit claim is required to connect the research question to evidence.",
        ),
        _dimension(
            "evidence_coverage",
            "Evidence coverage",
            evidence_status,
            {
                "claims": claim_count,
                "claims_with_evidence": claims_with_evidence,
                "evidence_items": evidence_count,
            },
            "Every claim should have attached evidence before it is treated as supported or contradicted.",
        ),
        _dimension(
            "evidence_type_diversity",
            "Evidence-type diversity",
            diversity_status,
            {"evidence_types": len(evidence_types), "evidence_items": evidence_count},
            "Multiple evidence types can reduce dependence on a single source category.",
        ),
        _dimension(
            "human_validation_judgments",
            "Human validation judgments",
            judgment_status,
            {
                "claims": claim_count,
                "judgments": len(judgments),
                "current_judgments": current_judgments,
            },
            "Each claim should have a current user-authored judgment after its latest evidence changes.",
        ),
        _dimension(
            "synthesis_findings",
            "Synthesis findings",
            synthesis_status,
            {"sections_present": int(bool(synthesis and synthesis.findings))},
            "A synthesis should state what the stored evidence currently justifies.",
        ),
        _dimension(
            "recorded_limitations",
            "Recorded limitations",
            limitations_status,
            {"sections_present": int(bool(synthesis and synthesis.limitations))},
            "Explicit limitations make the boundaries of the investigation visible.",
        ),
        _dimension(
            "unresolved_questions",
            "Unresolved questions",
            unresolved_status,
            {"sections_present": int(bool(synthesis and synthesis.unresolved_questions))},
            "Open questions should be recorded rather than hidden by a completed narrative.",
        ),
    ]

    recommendation_by_key = {
        "claim_coverage": "Add at least one explicit claim that can be evaluated against evidence.",
        "evidence_coverage": "Attach evidence to every claim, including evidence that may contradict it.",
        "evidence_type_diversity": "Add evidence from another source type where it would materially test the claims.",
        "human_validation_judgments": "Record or refresh a user-authored validation judgment for every claim.",
        "synthesis_findings": "Write a synthesis that states only what the stored evidence currently supports.",
        "recorded_limitations": "Document the investigation's evidence, method, and scope limitations.",
        "unresolved_questions": "Record the important questions that remain unresolved.",
    }
    recommendations = [
        recommendation_by_key[dimension.key]
        for dimension in dimensions
        if dimension.status != "complete"
    ]

    return InvestigationQualityAssessment(
        investigation_id=report.investigation_id,
        dimensions=dimensions,
        recommendations=recommendations,
        generated_from_stored_state_at=report.generated_from_stored_state_at,
    )
