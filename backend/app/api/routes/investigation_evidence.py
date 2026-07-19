from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.investigation_evidence import ClaimEvidence, ClaimValidationJudgment, InvestigationClaim
from app.models.user import User
from app.schemas.investigation_evidence import (
    ClaimAssessmentUpdate,
    ClaimCreate,
    ClaimRead,
    ClaimUpdate,
    ClaimValidationJudgmentCreate,
    ClaimValidationJudgmentRead,
    ClaimValidationSummary,
    EvidenceAssessmentUpdate,
    EvidenceCreate,
    EvidenceRead,
    EvidenceUpdate,
    InvestigationEducationRecommendations,
    InvestigationValidationSummary,
    ResearchLearningRecommendation,
)
from app.services.education import LESSON_BY_SLUG

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


def _owned_claim(db: Session, user_id: int, claim_id: int) -> InvestigationClaim:
    claim = db.scalar(
        select(InvestigationClaim)
        .join(Investigation, Investigation.id == InvestigationClaim.investigation_id)
        .where(InvestigationClaim.id == claim_id, Investigation.owner_id == user_id)
    )
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def _owned_evidence(db: Session, user_id: int, evidence_id: int) -> ClaimEvidence:
    evidence = db.scalar(
        select(ClaimEvidence)
        .join(InvestigationClaim, InvestigationClaim.id == ClaimEvidence.claim_id)
        .join(Investigation, Investigation.id == InvestigationClaim.investigation_id)
        .where(ClaimEvidence.id == evidence_id, Investigation.owner_id == user_id)
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


def _claim_evidence(db: Session, claim_id: int) -> list[ClaimEvidence]:
    return list(db.scalars(select(ClaimEvidence).where(ClaimEvidence.claim_id == claim_id)).all())


def _latest_evidence_update(evidence: list[ClaimEvidence]):
    return max((item.updated_at for item in evidence), default=None)


def _latest_judgment(db: Session, claim_id: int) -> ClaimValidationJudgment | None:
    return db.scalar(
        select(ClaimValidationJudgment)
        .where(ClaimValidationJudgment.claim_id == claim_id)
        .order_by(ClaimValidationJudgment.reviewed_at.desc(), ClaimValidationJudgment.id.desc())
        .limit(1)
    )


def _judgment_read(
    judgment: ClaimValidationJudgment,
    claim: InvestigationClaim,
    latest_evidence_update,
) -> ClaimValidationJudgmentRead:
    evidence_is_stale = latest_evidence_update is not None and (
        judgment.evidence_updated_at_snapshot is None
        or latest_evidence_update > judgment.evidence_updated_at_snapshot
    )
    return ClaimValidationJudgmentRead(
        id=judgment.id,
        claim_id=judgment.claim_id,
        reviewer_id=judgment.reviewer_id,
        validation_status=judgment.validation_status,
        confidence_level=judgment.confidence_level,
        rationale=judgment.rationale,
        unresolved_questions=judgment.unresolved_questions,
        reviewed_at=judgment.reviewed_at,
        is_stale=claim.updated_at > judgment.claim_updated_at_snapshot or evidence_is_stale,
    )


def _claim_summary(db: Session, claim: InvestigationClaim) -> ClaimValidationSummary:
    evidence = _claim_evidence(db, claim.id)
    supporting_count = sum(item.relationship == "supports" for item in evidence)
    contradicting_count = sum(item.relationship == "contradicts" for item in evidence)
    neutral_count = sum(item.relationship == "neutral" for item in evidence)
    assessed_evidence_count = sum(item.credibility_rating is not None for item in evidence)
    return ClaimValidationSummary(
        claim_id=claim.id,
        confidence_level=claim.confidence_level,
        supporting_count=supporting_count,
        contradicting_count=contradicting_count,
        neutral_count=neutral_count,
        assessed_evidence_count=assessed_evidence_count,
        total_evidence_count=len(evidence),
        has_unresolved_contradiction=contradicting_count > 0,
    )


def _recommendation(lesson_slug: str, gap_type: str, priority: int, reason: str) -> ResearchLearningRecommendation:
    lesson = LESSON_BY_SLUG[lesson_slug]
    return ResearchLearningRecommendation(
        competency=lesson["competency"],
        lesson_slug=lesson_slug,
        lesson_title=lesson["title"],
        gap_type=gap_type,
        priority=priority,
        reason=reason,
    )


def _education_recommendations(db: Session, investigation_id: int) -> list[ResearchLearningRecommendation]:
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    recommendations: dict[tuple[str, str], ResearchLearningRecommendation] = {}

    def add(item: ResearchLearningRecommendation) -> None:
        key = (item.lesson_slug, item.gap_type)
        current = recommendations.get(key)
        if current is None or item.priority > current.priority:
            recommendations[key] = item

    if not claims:
        add(
            _recommendation(
                "research-thesis-construction",
                "missing_claims",
                5,
                "Define at least one falsifiable claim so the investigation can be tested against evidence.",
            )
        )

    for claim in claims:
        evidence = _claim_evidence(db, claim.id)
        latest_update = _latest_evidence_update(evidence)
        judgment = _latest_judgment(db, claim.id)

        if not evidence:
            add(
                _recommendation(
                    "evidence-quality-and-bias",
                    "missing_evidence",
                    5,
                    "A claim has no attached evidence; practice identifying primary sources and separating evidence from narrative.",
                )
            )
        if any(item.relationship == "contradicts" for item in evidence):
            add(
                _recommendation(
                    "research-thesis-construction",
                    "contradictory_evidence",
                    5,
                    "Contradictory evidence is unresolved; strengthen falsifiability, assumptions, and decision criteria before concluding.",
                )
            )
        if evidence and any(item.credibility_rating is None for item in evidence):
            add(
                _recommendation(
                    "evidence-quality-and-bias",
                    "unassessed_credibility",
                    4,
                    "One or more evidence sources lack a credibility assessment, so source quality and bias should be reviewed.",
                )
            )
        if claim.confidence_level in {None, "low"}:
            add(
                _recommendation(
                    "research-thesis-construction",
                    "low_claim_confidence",
                    4,
                    "A claim is unassessed or low confidence; refine its assumptions and identify what evidence would change the conclusion.",
                )
            )
        if judgment is None:
            add(
                _recommendation(
                    "research-thesis-construction",
                    "missing_validation_judgment",
                    4,
                    "A claim has no validation judgment; document status, confidence, rationale, and unresolved questions.",
                )
            )
            continue

        judgment_read = _judgment_read(judgment, claim, latest_update)
        if judgment_read.is_stale:
            add(
                _recommendation(
                    "evidence-quality-and-bias",
                    "stale_validation",
                    5,
                    "A validation judgment predates later claim or evidence changes; reassess the updated evidence before relying on it.",
                )
            )
        if judgment.unresolved_questions:
            add(
                _recommendation(
                    "research-thesis-construction",
                    "unresolved_questions",
                    4,
                    "The latest validation judgment records unresolved questions; turn them into explicit tests and decision criteria.",
                )
            )
        if judgment.validation_status in {"mixed", "contradicted", "insufficient", "unreviewed"}:
            add(
                _recommendation(
                    "research-thesis-construction",
                    "inconclusive_validation",
                    3,
                    "The latest validation status is not fully supported; strengthen the thesis and define the evidence needed for resolution.",
                )
            )

    return sorted(recommendations.values(), key=lambda item: (-item.priority, item.lesson_slug, item.gap_type))


@router.post(
    "/{investigation_id}/claims",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    investigation_id: int,
    payload: ClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationClaim:
    _owned_investigation(db, current_user.id, investigation_id)
    claim = InvestigationClaim(investigation_id=investigation_id, statement=payload.statement)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/{investigation_id}/claims", response_model=list[ClaimRead])
def list_claims(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvestigationClaim]:
    _owned_investigation(db, current_user.id, investigation_id)
    return list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.updated_at.desc(), InvestigationClaim.id.desc())
        ).all()
    )


@router.get(
    "/{investigation_id}/education-recommendations",
    response_model=InvestigationEducationRecommendations,
)
def get_investigation_education_recommendations(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationEducationRecommendations:
    _owned_investigation(db, current_user.id, investigation_id)
    recommendations = _education_recommendations(db, investigation_id)
    return InvestigationEducationRecommendations(
        investigation_id=investigation_id,
        recommendation_count=len(recommendations),
        completion_authority="adaptive_assessment_only",
        recommendations=recommendations,
    )


@router.patch("/claims/{claim_id}", response_model=ClaimRead)
def update_claim(
    claim_id: int,
    payload: ClaimUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationClaim:
    claim = _owned_claim(db, current_user.id, claim_id)
    claim.statement = payload.statement
    db.commit()
    db.refresh(claim)
    return claim


@router.patch("/claims/{claim_id}/assessment", response_model=ClaimRead)
def update_claim_assessment(
    claim_id: int,
    payload: ClaimAssessmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationClaim:
    claim = _owned_claim(db, current_user.id, claim_id)
    claim.confidence_level = payload.confidence_level
    claim.confidence_rationale = payload.confidence_rationale
    db.commit()
    db.refresh(claim)
    return claim


@router.post(
    "/claims/{claim_id}/judgments",
    response_model=ClaimValidationJudgmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_claim_judgment(
    claim_id: int,
    payload: ClaimValidationJudgmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimValidationJudgmentRead:
    claim = _owned_claim(db, current_user.id, claim_id)
    latest_evidence_update = _latest_evidence_update(_claim_evidence(db, claim.id))
    judgment = ClaimValidationJudgment(
        claim_id=claim.id,
        reviewer_id=current_user.id,
        validation_status=payload.validation_status,
        confidence_level=payload.confidence_level,
        rationale=payload.rationale,
        unresolved_questions=payload.unresolved_questions,
        claim_updated_at_snapshot=claim.updated_at,
        evidence_updated_at_snapshot=latest_evidence_update,
    )
    db.add(judgment)
    db.commit()
    db.refresh(judgment)
    return _judgment_read(judgment, claim, latest_evidence_update)


@router.get("/claims/{claim_id}/judgments", response_model=list[ClaimValidationJudgmentRead])
def list_claim_judgments(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClaimValidationJudgmentRead]:
    claim = _owned_claim(db, current_user.id, claim_id)
    latest_evidence_update = _latest_evidence_update(_claim_evidence(db, claim.id))
    judgments = list(
        db.scalars(
            select(ClaimValidationJudgment)
            .where(ClaimValidationJudgment.claim_id == claim.id)
            .order_by(ClaimValidationJudgment.reviewed_at.desc(), ClaimValidationJudgment.id.desc())
        ).all()
    )
    return [_judgment_read(item, claim, latest_evidence_update) for item in judgments]


@router.get("/claims/{claim_id}/summary", response_model=ClaimValidationSummary)
def get_claim_summary(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimValidationSummary:
    claim = _owned_claim(db, current_user.id, claim_id)
    return _claim_summary(db, claim)


@router.get("/{investigation_id}/validation-summary", response_model=InvestigationValidationSummary)
def get_investigation_validation_summary(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationValidationSummary:
    _owned_investigation(db, current_user.id, investigation_id)
    claims = list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.id)
        ).all()
    )
    summaries = [_claim_summary(db, claim) for claim in claims]
    return InvestigationValidationSummary(
        investigation_id=investigation_id,
        claim_count=len(claims),
        assessed_claim_count=sum(claim.confidence_level is not None for claim in claims),
        low_confidence_count=sum(claim.confidence_level == "low" for claim in claims),
        medium_confidence_count=sum(claim.confidence_level == "medium" for claim in claims),
        high_confidence_count=sum(claim.confidence_level == "high" for claim in claims),
        unresolved_contradiction_count=sum(summary.has_unresolved_contradiction for summary in summaries),
        claims=summaries,
    )


@router.delete("/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    claim = _owned_claim(db, current_user.id, claim_id)
    db.delete(claim)
    db.commit()


@router.post(
    "/claims/{claim_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    claim_id: int,
    payload: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidence:
    _owned_claim(db, current_user.id, claim_id)
    evidence = ClaimEvidence(claim_id=claim_id, **payload.model_dump())
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/claims/{claim_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClaimEvidence]:
    _owned_claim(db, current_user.id, claim_id)
    return list(
        db.scalars(
            select(ClaimEvidence)
            .where(ClaimEvidence.claim_id == claim_id)
            .order_by(ClaimEvidence.updated_at.desc(), ClaimEvidence.id.desc())
        ).all()
    )


@router.patch("/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence(
    evidence_id: int,
    payload: EvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidence:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    for field_name, value in payload.model_dump().items():
        setattr(evidence, field_name, value)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.patch("/evidence/{evidence_id}/assessment", response_model=EvidenceRead)
def update_evidence_assessment(
    evidence_id: int,
    payload: EvidenceAssessmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidence:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    evidence.credibility_rating = payload.credibility_rating
    evidence.credibility_rationale = payload.credibility_rationale
    db.commit()
    db.refresh(evidence)
    return evidence


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    db.delete(evidence)
    db.commit()
