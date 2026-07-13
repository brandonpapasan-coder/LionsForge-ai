from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.executive_intelligence import ExecutiveIntelligenceBriefRead
from app.services.executive_intelligence_service import build_executive_brief

router = APIRouter()


@router.get("/projects/{project_id}", response_model=ExecutiveIntelligenceBriefRead)
def get_executive_intelligence_brief(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveIntelligenceBriefRead:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")

    return ExecutiveIntelligenceBriefRead(
        **build_executive_brief(db, current_user.id, project)
    )
