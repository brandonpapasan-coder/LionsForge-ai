from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.multi_agent_consensus import MultiAgentConsensusRead
from app.services.multi_agent_consensus_service import build_project_consensus

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


@router.get("/projects/{project_id}", response_model=MultiAgentConsensusRead)
def get_project_consensus(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MultiAgentConsensusRead:
    _owned_project(db, current_user.id, project_id)
    return MultiAgentConsensusRead(**build_project_consensus(db, current_user.id, project_id))
