from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.research_session import ResearchSessionCreate, ResearchSessionRead, ResearchSessionUpdate

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


def _owned_session(db: Session, owner_id: int, session_id: int) -> ResearchSession:
    session = db.scalar(
        select(ResearchSession)
        .join(ResearchProject, ResearchSession.project_id == ResearchProject.id)
        .where(
            ResearchSession.id == session_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    return session


@router.post(
    "/research-projects/{project_id}/sessions",
    response_model=ResearchSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    project_id: int,
    payload: ResearchSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchSession:
    _owned_project(db, current_user.id, project_id)
    session = ResearchSession(project_id=project_id, **payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/research-projects/{project_id}/sessions", response_model=list[ResearchSessionRead])
def list_sessions(
    project_id: int,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchSession]:
    _owned_project(db, current_user.id, project_id)
    statement = select(ResearchSession).where(ResearchSession.project_id == project_id)
    if not include_archived:
        statement = statement.where(ResearchSession.status != "archived")
    return list(db.scalars(statement.order_by(desc(ResearchSession.updated_at))).all())


@router.get("/research-sessions/{session_id}", response_model=ResearchSessionRead)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchSession:
    return _owned_session(db, current_user.id, session_id)


@router.patch("/research-sessions/{session_id}", response_model=ResearchSessionRead)
def update_session(
    session_id: int,
    payload: ResearchSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchSession:
    session = _owned_session(db, current_user.id, session_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/research-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    session = _owned_session(db, current_user.id, session_id)
    session.status = "archived"
    db.commit()
