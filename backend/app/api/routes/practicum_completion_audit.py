from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.practicum_completion_export import export_completion_bundle, validate_completion_bundle

router = APIRouter()


@router.get("/enrollments/{enrollment_id}/completion-audit")
def export_practicum_completion_audit(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_completion_bundle(db, enrollment_id=enrollment_id, user=current_user)


@router.post("/completion-audit/validate")
def validate_practicum_completion_audit(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_completion_bundle(payload)
