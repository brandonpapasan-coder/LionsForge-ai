from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_evidence import ResearchEvidence
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.research_evidence import ResearchEvidenceCreate, ResearchEvidenceRead, ResearchEvidenceUpdate

router = APIRouter()


def _owned_session(db: Session, owner_id: int, session_id: int) -> ResearchSession:
    session = db.scalar(
        select(ResearchSession)
        .join(ResearchProject, ResearchSession.project_id == ResearchProject.id)
        .where(ResearchSession.id == session_id, ResearchProject.owner_id == owner_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    return session


def _owned_evidence(db: Session, owner_id: int, evidence_id: int) -> ResearchEvidence:
    evidence = db.scalar(
        select(ResearchEvidence)
        .join(ResearchProject, ResearchEvidence.project_id == ResearchProject.id)
        .where(ResearchEvidence.id == evidence_id, ResearchProject.owner_id == owner_id)
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Research evidence not found")
    return evidence


@router.post(
    "/research-sessions/{session_id}/evidence",
    response_model=ResearchEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    session_id: int,
    payload: ResearchEvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchEvidence:
    session = _owned_session(db, current_user.id, session_id)
    evidence = ResearchEvidence(project_id=session.project_id, session_id=session.id, **payload.model_dump())
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/research-sessions/{session_id}/evidence", response_model=list[ResearchEvidenceRead])
def list_evidence(
    session_id: int,
    query: str | None = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchEvidence]:
    _owned_session(db, current_user.id, session_id)
    statement = select(ResearchEvidence).where(ResearchEvidence.session_id == session_id)
    if not include_archived:
        statement = statement.where(ResearchEvidence.status != "archived")
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(ResearchEvidence.title.ilike(pattern), ResearchEvidence.summary.ilike(pattern))
        )
    return list(db.scalars(statement.order_by(desc(ResearchEvidence.updated_at))).all())


@router.get("/evidence/{evidence_id}", response_model=ResearchEvidenceRead)
def get_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchEvidence:
    return _owned_evidence(db, current_user.id, evidence_id)


@router.patch("/evidence/{evidence_id}", response_model=ResearchEvidenceRead)
def update_evidence(
    evidence_id: int,
    payload: ResearchEvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchEvidence:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(evidence, field, value)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    evidence.status = "archived"
    db.commit()
