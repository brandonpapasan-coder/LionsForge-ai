from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.research_practicum import PracticumReadinessRead, PracticumReviewDecisionCreate
from app.services import research_practicum_reviewer as reviewer_service

router = APIRouter()


@router.post(
    "/enrollments/{enrollment_id}/reviews",
    response_model=PracticumReadinessRead,
    deprecated=True,
)
def review_practicum_compatibility(
    enrollment_id: int,
    payload: PracticumReviewDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReadinessRead:
    """Preserve the legacy review URL while using the canonical reviewer service."""
    reviewer_service.require_reviewer(current_user)
    detail = reviewer_service.record_decision(
        db,
        enrollment_id=enrollment_id,
        reviewer=current_user,
        payload=payload,
    )
    return detail.readiness
