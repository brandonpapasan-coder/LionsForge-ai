from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.research_conclusion import ResearchConclusion, ResearchConclusionRevision
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_conclusion_workspace import (
    ResearchConclusionDraftUpdate,
    ResearchConclusionRevision as ResearchConclusionRevisionSchema,
    ResearchConclusionWorkspace,
)

router = APIRouter()
DISCLAIMER = (
    "Conclusion text is authored and controlled by the project owner. Readiness describes workflow completeness "
    "and provenance risk only; it does not certify truth, accuracy, completeness, or predictive validity."
)


def _project_or_404(db: Session, owner_id: int, project_id: int) -> ResearchProject:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return project


def _validated_evidence_ids(db: Session, owner_id: int, project_id: int, evidence_ids: list[int]) -> list[int]:
    if not evidence_ids:
        return []
    found = set(
        db.scalars(
            select(EvidenceRecord.id).where(
                EvidenceRecord.owner_id == owner_id,
                EvidenceRecord.project_id == project_id,
                EvidenceRecord.id.in_(evidence_ids),
            )
        ).all()
    )
    missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in found]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"message": "Evidence references must belong to this owner and project", "evidence_ids": missing},
        )
    return evidence_ids


def _workspace(db: Session, owner_id: int, project_id: int) -> ResearchConclusionWorkspace:
    conclusion = db.scalar(
        select(ResearchConclusion).where(
            ResearchConclusion.owner_id == owner_id,
            ResearchConclusion.project_id == project_id,
        )
    )
    if conclusion is None:
        return ResearchConclusionWorkspace(
            id=None,
            project_id=project_id,
            status="draft",
            conclusion_text="",
            evidence_ids=[],
            revision_count=0,
            finalized_at=None,
            created_at=None,
            updated_at=None,
            revisions=[],
            disclaimer=DISCLAIMER,
        )
    revisions = list(
        db.scalars(
            select(ResearchConclusionRevision)
            .where(
                ResearchConclusionRevision.conclusion_id == conclusion.id,
                ResearchConclusionRevision.owner_id == owner_id,
            )
            .order_by(ResearchConclusionRevision.revision_number.desc())
        ).all()
    )
    return ResearchConclusionWorkspace(
        id=conclusion.id,
        project_id=project_id,
        status=conclusion.status,
        conclusion_text=conclusion.conclusion_text,
        evidence_ids=conclusion.evidence_ids,
        revision_count=len(revisions),
        finalized_at=conclusion.finalized_at,
        created_at=conclusion.created_at,
        updated_at=conclusion.updated_at,
        revisions=[ResearchConclusionRevisionSchema.model_validate(item) for item in revisions],
        disclaimer=DISCLAIMER,
    )


@router.get("/projects/{project_id}", response_model=ResearchConclusionWorkspace)
def get_conclusion_workspace(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchConclusionWorkspace:
    _project_or_404(db, current_user.id, project_id)
    return _workspace(db, current_user.id, project_id)


@router.put("/projects/{project_id}", response_model=ResearchConclusionWorkspace)
def update_conclusion_workspace(
    project_id: int,
    payload: ResearchConclusionDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchConclusionWorkspace:
    _project_or_404(db, current_user.id, project_id)
    evidence_ids = _validated_evidence_ids(db, current_user.id, project_id, payload.evidence_ids)
    text = payload.conclusion_text.strip()
    if payload.finalize and (not payload.confirmed or not text):
        raise HTTPException(status_code=400, detail="Finalization requires confirmation and a non-empty conclusion")

    conclusion = db.scalar(
        select(ResearchConclusion).where(
            ResearchConclusion.owner_id == current_user.id,
            ResearchConclusion.project_id == project_id,
        )
    )
    if conclusion is None:
        conclusion = ResearchConclusion(
            owner_id=current_user.id,
            project_id=project_id,
            conclusion_text="",
            evidence_ids=[],
            status="draft",
        )
        db.add(conclusion)
        db.flush()

    if conclusion.status == "finalized" and not payload.confirmed:
        raise HTTPException(status_code=400, detail="Revising a finalized conclusion requires explicit confirmation")

    changed = conclusion.conclusion_text != text or conclusion.evidence_ids != evidence_ids or payload.finalize
    if not changed:
        return _workspace(db, current_user.id, project_id)

    revision_number = int(
        db.scalar(
            select(func.coalesce(func.max(ResearchConclusionRevision.revision_number), 0)).where(
                ResearchConclusionRevision.conclusion_id == conclusion.id
            )
        )
        or 0
    ) + 1
    status = "finalized" if payload.finalize else ("revised" if revision_number > 1 else "draft")
    now = datetime.utcnow()
    conclusion.conclusion_text = text
    conclusion.evidence_ids = evidence_ids
    conclusion.status = status
    conclusion.finalized_at = now if payload.finalize else None
    conclusion.updated_at = now
    db.add(
        ResearchConclusionRevision(
            conclusion_id=conclusion.id,
            owner_id=current_user.id,
            project_id=project_id,
            revision_number=revision_number,
            conclusion_text=text,
            evidence_ids=evidence_ids,
            revision_note=payload.revision_note,
            status=status,
        )
    )
    db.commit()
    return _workspace(db, current_user.id, project_id)
