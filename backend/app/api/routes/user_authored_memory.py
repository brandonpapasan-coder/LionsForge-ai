from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.knowledge_memory import KnowledgeMemoryCreate, KnowledgeMemoryRead
from app.services.knowledge_memory_service import revisions_for
from app.services.user_authored_memory_service import create_user_authored_memory

router = APIRouter()


@router.post("", response_model=KnowledgeMemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: KnowledgeMemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == payload.project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")

    try:
        memory, _created = create_user_authored_memory(
            db,
            owner_id=current_user.id,
            **payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return KnowledgeMemoryRead(
        **{
            column.name: getattr(memory, column.name)
            for column in memory.__table__.columns
        },
        revisions=revisions_for(db, memory.id),
    )
