from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.research_conclusion import ResearchConclusion, ResearchConclusionRevision
from app.models.research_conclusion_defense import ResearchConclusionDefense, ResearchConclusionDefenseRevision
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_conclusion_defense_review import ResearchConclusionDefenseUpdate, ResearchConclusionDefenseWorkspace

router = APIRouter()
SECTIONS = ("evidence_coverage", "strongest_counterargument", "known_limitations", "unresolved_questions", "confidence_rationale")
DISCLAIMER = "This review records the user's own critical reflection. Completeness only means all reflection sections were supplied; it does not grade, approve, publish, or certify the conclusion."


def _project(project_id: int, user_id: int, db: Session) -> ResearchProject:
    item = db.scalar(select(ResearchProject).where(ResearchProject.id == project_id, ResearchProject.owner_id == user_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return item


def _state(payload: ResearchConclusionDefenseUpdate) -> tuple[str, list[str]]:
    missing = [name for name in SECTIONS if not getattr(payload, name).strip()]
    return ("complete" if not missing else "incomplete", missing)


def _validate_links(payload: ResearchConclusionDefenseUpdate, project_id: int, user_id: int, db: Session) -> None:
    conclusion = db.scalar(select(ResearchConclusion).where(ResearchConclusion.project_id == project_id, ResearchConclusion.owner_id == user_id))
    if payload.conclusion_revision_number is not None:
        if conclusion is None:
            raise HTTPException(status_code=422, detail="Conclusion revision not found")
        revision = db.scalar(select(ResearchConclusionRevision).where(ResearchConclusionRevision.conclusion_id == conclusion.id, ResearchConclusionRevision.revision_number == payload.conclusion_revision_number, ResearchConclusionRevision.owner_id == user_id, ResearchConclusionRevision.project_id == project_id))
        if revision is None:
            raise HTTPException(status_code=422, detail="Conclusion revision not found")
    if payload.evidence_ids:
        found = set(db.scalars(select(EvidenceRecord.id).where(EvidenceRecord.id.in_(payload.evidence_ids), EvidenceRecord.owner_id == user_id, EvidenceRecord.project_id == project_id)).all())
        invalid = [item for item in payload.evidence_ids if item not in found]
        if invalid:
            raise HTTPException(status_code=422, detail={"message": "Invalid evidence references", "evidence_ids": invalid})


def _response(item: ResearchConclusionDefense | None, project_id: int, db: Session) -> ResearchConclusionDefenseWorkspace:
    if item is None:
        return ResearchConclusionDefenseWorkspace(id=None, project_id=project_id, conclusion_revision_number=None, evidence_ids=[], evidence_coverage="", strongest_counterargument="", known_limitations="", unresolved_questions="", confidence_rationale="", status="incomplete", missing_sections=list(SECTIONS), revision_count=0, created_at=None, updated_at=None, revisions=[], disclaimer=DISCLAIMER)
    revisions = list(db.scalars(select(ResearchConclusionDefenseRevision).where(ResearchConclusionDefenseRevision.defense_id == item.id).order_by(ResearchConclusionDefenseRevision.revision_number.desc())).all())
    return ResearchConclusionDefenseWorkspace(id=item.id, project_id=project_id, conclusion_revision_number=item.conclusion_revision_number, evidence_ids=item.evidence_ids, evidence_coverage=item.evidence_coverage, strongest_counterargument=item.strongest_counterargument, known_limitations=item.known_limitations, unresolved_questions=item.unresolved_questions, confidence_rationale=item.confidence_rationale, status=item.status, missing_sections=item.missing_sections, revision_count=item.revision_count, created_at=item.created_at, updated_at=item.updated_at, revisions=revisions, disclaimer=DISCLAIMER)


@router.get("/projects/{project_id}", response_model=ResearchConclusionDefenseWorkspace)
def get_defense_review(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ResearchConclusionDefenseWorkspace:
    _project(project_id, current_user.id, db)
    item = db.scalar(select(ResearchConclusionDefense).where(ResearchConclusionDefense.owner_id == current_user.id, ResearchConclusionDefense.project_id == project_id))
    return _response(item, project_id, db)


@router.put("/projects/{project_id}", response_model=ResearchConclusionDefenseWorkspace)
def update_defense_review(payload: ResearchConclusionDefenseUpdate, project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ResearchConclusionDefenseWorkspace:
    _project(project_id, current_user.id, db)
    _validate_links(payload, project_id, current_user.id, db)
    status, missing = _state(payload)
    item = db.scalar(select(ResearchConclusionDefense).where(ResearchConclusionDefense.owner_id == current_user.id, ResearchConclusionDefense.project_id == project_id))
    values = {name: getattr(payload, name) for name in SECTIONS}
    values.update(conclusion_revision_number=payload.conclusion_revision_number, evidence_ids=payload.evidence_ids, status=status, missing_sections=missing)
    if item is not None and all(getattr(item, key) == value for key, value in values.items()):
        return _response(item, project_id, db)
    if item is None:
        item = ResearchConclusionDefense(owner_id=current_user.id, project_id=project_id, revision_count=0, **values)
        db.add(item)
        db.flush()
    else:
        for key, value in values.items():
            setattr(item, key, value)
    item.revision_count += 1
    db.add(ResearchConclusionDefenseRevision(defense_id=item.id, owner_id=current_user.id, project_id=project_id, revision_number=item.revision_count, revision_note=payload.revision_note, **values))
    db.commit()
    db.refresh(item)
    return _response(item, project_id, db)
