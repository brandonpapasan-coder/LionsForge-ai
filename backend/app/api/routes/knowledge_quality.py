from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.knowledge_quality import (
    KnowledgeQualityActivity,
    KnowledgeQualityDashboard,
    KnowledgeQualityRisk,
)
from app.services.knowledge_quality_service import build_knowledge_quality_dashboard

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


@router.get("/dashboard", response_model=KnowledgeQualityDashboard)
def get_organization_knowledge_quality(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeQualityDashboard:
    return KnowledgeQualityDashboard.model_validate(
        build_knowledge_quality_dashboard(db, current_user.id)
    )


@router.get(
    "/projects/{project_id}",
    response_model=KnowledgeQualityDashboard,
)
def get_project_knowledge_quality(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeQualityDashboard:
    _owned_project(db, current_user.id, project_id)
    return KnowledgeQualityDashboard.model_validate(
        build_knowledge_quality_dashboard(db, current_user.id, project_id)
    )


@router.get(
    "/projects/{project_id}/risks",
    response_model=list[KnowledgeQualityRisk],
)
def get_project_knowledge_risks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeQualityRisk]:
    _owned_project(db, current_user.id, project_id)
    dashboard = build_knowledge_quality_dashboard(db, current_user.id, project_id)
    return [KnowledgeQualityRisk.model_validate(item) for item in dashboard["top_risks"]]


@router.get(
    "/projects/{project_id}/activity",
    response_model=list[KnowledgeQualityActivity],
)
def get_project_knowledge_activity(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeQualityActivity]:
    _owned_project(db, current_user.id, project_id)
    dashboard = build_knowledge_quality_dashboard(db, current_user.id, project_id)
    return [
        KnowledgeQualityActivity.model_validate(item)
        for item in dashboard["recent_activity"]
    ]
