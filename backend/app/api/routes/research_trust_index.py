from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_trust_index import (
    GovernanceExecutiveSummary,
    ProjectGovernanceSnapshotRead,
    ResearchTrustIndexRead,
)
from app.services.research_trust_index_service import calculate_project_rti

router = APIRouter()


def _owned_project(db: Session, owner_id: int, project_id: int) -> ResearchProject:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return project


def _executive_summary(trust_index: ResearchTrustIndexRead) -> GovernanceExecutiveSummary:
    if trust_index.overall_score >= 80:
        trust_status = "strong"
    elif trust_index.overall_score >= 60:
        trust_status = "moderate"
    else:
        trust_status = "weak"

    if trust_index.conflict_count or trust_index.review_reversal_count >= 3:
        risk_level = "high"
    elif trust_index.overall_score < 60 or trust_index.review_reversal_count:
        risk_level = "elevated"
    else:
        risk_level = "controlled"

    evidence_review_rate = (
        trust_index.reviewed_evidence_count / trust_index.evidence_count
        if trust_index.evidence_count
        else 0.0
    )
    approval_rate = (
        trust_index.approved_count / trust_index.evidence_count
        if trust_index.evidence_count
        else 0.0
    )
    headline = (
        f"Research trust is {trust_status} with {risk_level} governance risk; "
        f"{trust_index.reviewed_evidence_count} of {trust_index.evidence_count} evidence records have review history."
    )
    return GovernanceExecutiveSummary(
        trust_status=trust_status,
        risk_level=risk_level,
        headline=headline,
        evidence_review_rate=round(evidence_review_rate, 4),
        approval_rate=round(approval_rate, 4),
        key_strengths=trust_index.strengths[:3],
        key_risks=trust_index.limitations[:3],
        priority_actions=trust_index.recommended_actions[:5],
    )


@router.get("/projects/{project_id}", response_model=ResearchTrustIndexRead)
def get_project_trust_index(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchTrustIndexRead:
    _owned_project(db, current_user.id, project_id)
    return ResearchTrustIndexRead(**calculate_project_rti(db, current_user.id, project_id))


@router.get("/projects/{project_id}/governance-snapshot", response_model=ProjectGovernanceSnapshotRead)
def get_project_governance_snapshot(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectGovernanceSnapshotRead:
    project = _owned_project(db, current_user.id, project_id)
    review_history = list(
        db.scalars(
            select(EvidenceReviewEvent)
            .join(EvidenceRecord, EvidenceReviewEvent.evidence_id == EvidenceRecord.id)
            .where(
                EvidenceReviewEvent.owner_id == current_user.id,
                EvidenceRecord.owner_id == current_user.id,
                EvidenceRecord.project_id == project_id,
            )
            .order_by(EvidenceReviewEvent.created_at.asc(), EvidenceReviewEvent.id.asc())
        ).all()
    )
    trust_index = ResearchTrustIndexRead(**calculate_project_rti(db, current_user.id, project_id))
    return ProjectGovernanceSnapshotRead(
        project_id=project.id,
        project_title=project.title,
        project_status=project.status,
        generated_at=datetime.utcnow(),
        executive_summary=_executive_summary(trust_index),
        trust_index=trust_index,
        review_history=review_history,
    )
