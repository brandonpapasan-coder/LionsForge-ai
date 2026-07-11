from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_project import ResearchProjectCreate, ResearchProjectRead, ResearchProjectUpdate

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


@router.post("", response_model=ResearchProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ResearchProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchProject:
    project = ResearchProject(owner_id=current_user.id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ResearchProjectRead])
def list_projects(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchProject]:
    statement = select(ResearchProject).where(ResearchProject.owner_id == current_user.id)
    if not include_archived:
        statement = statement.where(ResearchProject.status != "archived")
    return list(db.scalars(statement.order_by(desc(ResearchProject.updated_at))).all())


@router.get("/{project_id}", response_model=ResearchProjectRead)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchProject:
    return _owned_project(db, current_user.id, project_id)


@router.patch("/{project_id}", response_model=ResearchProjectRead)
def update_project(
    project_id: int,
    payload: ResearchProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchProject:
    project = _owned_project(db, current_user.id, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = _owned_project(db, current_user.id, project_id)
    project.status = "archived"
    db.commit()
