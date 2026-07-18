from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.personal_intelligence import (
    PersonalIntelligenceContextRequest,
    PersonalIntelligenceContextResponse,
)
from app.services.personal_intelligence_service import build_personal_intelligence_context

router = APIRouter()


@router.post("/context", response_model=PersonalIntelligenceContextResponse)
def create_personal_intelligence_context(
    payload: PersonalIntelligenceContextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalIntelligenceContextResponse:
    return build_personal_intelligence_context(
        db,
        owner_id=current_user.id,
        audience=payload.audience,
        project_id=payload.project_id,
        query=payload.query,
        limit=payload.limit,
        include_provisional=payload.include_provisional,
    )
