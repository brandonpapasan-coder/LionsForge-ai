from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mission import Mission, MissionStep
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.mission import MissionCreate, MissionRead
from app.services.mission_runtime_service import (
    advance_mission,
    cancel_mission,
    create_mission,
    mission_steps,
    retry_blocked_step,
    start_mission,
)

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


def _owned_mission(db: Session, owner_id: int, mission_id: int) -> Mission:
    mission = db.scalar(
        select(Mission).where(Mission.id == mission_id, Mission.owner_id == owner_id)
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


def _mission_read(db: Session, mission: Mission) -> MissionRead:
    return MissionRead(
        **{
            column.name: getattr(mission, column.name)
            for column in Mission.__table__.columns
        },
        steps=mission_steps(db, mission.id),
    )


@router.post("", response_model=MissionRead, status_code=status.HTTP_201_CREATED)
def create_research_mission(
    payload: MissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    project = _owned_project(db, current_user.id, payload.project_id)
    mission = create_mission(db, current_user.id, project, payload.model_dump())
    return _mission_read(db, mission)


@router.get("", response_model=list[MissionRead])
def list_research_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MissionRead]:
    missions = list(
        db.scalars(
            select(Mission)
            .where(Mission.owner_id == current_user.id)
            .order_by(desc(Mission.created_at), desc(Mission.id))
        ).all()
    )
    return [_mission_read(db, mission) for mission in missions]


@router.get("/{mission_id}", response_model=MissionRead)
def get_research_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    return _mission_read(db, _owned_mission(db, current_user.id, mission_id))


@router.post("/{mission_id}/start", response_model=MissionRead)
def start_research_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    mission = start_mission(db, _owned_mission(db, current_user.id, mission_id))
    return _mission_read(db, mission)


@router.post("/{mission_id}/advance", response_model=MissionRead)
def advance_research_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    mission = _owned_mission(db, current_user.id, mission_id)
    project = _owned_project(db, current_user.id, mission.project_id)
    mission = advance_mission(db, mission, project)
    return _mission_read(db, mission)


@router.post("/{mission_id}/steps/{step_id}/retry", response_model=MissionRead)
def retry_research_mission_step(
    mission_id: int,
    step_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    mission = _owned_mission(db, current_user.id, mission_id)
    step = db.scalar(
        select(MissionStep).where(MissionStep.id == step_id, MissionStep.mission_id == mission.id)
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Mission step not found")
    mission = retry_blocked_step(db, mission, step)
    return _mission_read(db, mission)


@router.post("/{mission_id}/cancel", response_model=MissionRead)
def cancel_research_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    mission = cancel_mission(db, _owned_mission(db, current_user.id, mission_id))
    return _mission_read(db, mission)
