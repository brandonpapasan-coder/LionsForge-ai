from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.learner_competency_gap_plan_export import (
    export_competency_gap_plan,
    validate_competency_gap_plan_bundle,
)

router = APIRouter()


@router.get("")
def get_learner_competency_gap_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_competency_gap_plan(db, user=current_user)


@router.post("/validate")
def validate_learner_competency_gap_plan(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_competency_gap_plan_bundle(payload)
