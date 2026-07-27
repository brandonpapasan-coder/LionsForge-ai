from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.roadmap_action_outcome_export import (
    export_roadmap_action_outcomes,
    validate_roadmap_action_outcome_bundle,
)

router = APIRouter()


@router.get("")
def get_roadmap_action_outcomes(
    template_slug: str | None = Query(default=None, min_length=1, max_length=120),
    reason_code: str | None = Query(default=None, min_length=1, max_length=80),
    outcome_status: str | None = Query(default=None, pattern="^(not_started|in_progress|review_ready|completed)$"),
    acted_after: datetime | None = None,
    acted_before: datetime | None = None,
    completed_after: datetime | None = None,
    completed_before: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_roadmap_action_outcomes(
        db,
        user=current_user,
        template_slug=template_slug,
        reason_code=reason_code,
        outcome_status=outcome_status,
        acted_after=acted_after,
        acted_before=acted_before,
        completed_after=completed_after,
        completed_before=completed_before,
    )


@router.post("/validate")
def validate_roadmap_action_outcomes(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_roadmap_action_outcome_bundle(payload)
