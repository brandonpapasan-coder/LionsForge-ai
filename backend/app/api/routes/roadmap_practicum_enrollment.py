from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.roadmap_practicum_enrollment_flow import (
    start_recommended_practicum,
    validate_roadmap_enrollment_bundle,
)

router = APIRouter()


class RoadmapEnrollmentCreate(BaseModel):
    template_slug: str = Field(min_length=1, max_length=120)
    template_version: int = Field(gt=0)
    research_project_id: int = Field(gt=0)


@router.post("")
def create_roadmap_practicum_enrollment(
    payload: RoadmapEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return start_recommended_practicum(
        db,
        user=current_user,
        template_slug=payload.template_slug,
        template_version=payload.template_version,
        research_project_id=payload.research_project_id,
    )


@router.post("/validate")
def validate_roadmap_practicum_enrollment(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_roadmap_enrollment_bundle(payload)
