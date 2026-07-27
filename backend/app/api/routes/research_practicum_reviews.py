from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.research_practicum import (
    PracticumReviewDecisionCreate,
    PracticumReviewerDetailRead,
    PracticumReviewerQueueRead,
)
from app.services.research_practicum_reviewer import (
    build_reviewer_detail,
    get_reviewable_enrollment,
    list_reviewer_queue as list_reviewer_queue_service,
    record_reviewer_decision as record_reviewer_decision_service,
    require_reviewer,
)

router = APIRouter()


@router.get("/queue", response_model=PracticumReviewerQueueRead)
def list_reviewer_queue(
    queue_status: str | None = Query(default=None, alias="status"),
    template_slug: str | None = None,
    learner_user_id: int | None = Query(default=None, gt=0),
    learner_query: str | None = Query(default=None, min_length=1, max_length=120),
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReviewerQueueRead:
    require_reviewer(current_user)
    return list_reviewer_queue_service(
        db,
        queue_status=queue_status,
        template_slug=template_slug,
        learner_user_id=learner_user_id,
        learner_query=learner_query,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        page=page,
        page_size=page_size,
    )


@router.get("/enrollments/{enrollment_id}", response_model=PracticumReviewerDetailRead)
def get_reviewer_detail(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReviewerDetailRead:
    require_reviewer(current_user)
    return build_reviewer_detail(db, get_reviewable_enrollment(db, enrollment_id))


@router.post("/enrollments/{enrollment_id}/decision", response_model=PracticumReviewerDetailRead)
def record_reviewer_decision(
    enrollment_id: int,
    payload: PracticumReviewDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReviewerDetailRead:
    require_reviewer(current_user)
    return record_reviewer_decision_service(
        db,
        enrollment=get_reviewable_enrollment(db, enrollment_id),
        reviewer=current_user,
        payload=payload,
    )
