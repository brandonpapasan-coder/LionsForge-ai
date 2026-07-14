from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_orchestration import ResearchOrchestrationRequest, ResearchOrchestrationResponse
from app.services.research_orchestration import ResearchOrchestrator

router = APIRouter()
orchestrator = ResearchOrchestrator()


def _verify_owned_project(db: Session, owner_id: int, project_id: int | None) -> None:
    if project_id is None:
        return
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")


@router.post("/run", response_model=ResearchOrchestrationResponse)
def run_research_orchestration(
    payload: ResearchOrchestrationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchOrchestrationResponse:
    _verify_owned_project(db, current_user.id, payload.project_id)
    return orchestrator.run(payload, current_user.id)
