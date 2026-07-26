from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.education import LessonProgress
from app.models.research_practicum import (
    PracticumEnrollment,
    PracticumObjective,
    PracticumObjectiveProgress,
    PracticumReviewDecision,
    PracticumTemplate,
)
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_practicum import (
    PracticumEnrollmentCreate,
    PracticumEnrollmentRead,
    PracticumObjectiveProgressRead,
    PracticumObjectiveProgressUpdate,
    PracticumTemplateRead,
)
from app.services.research_practicum_templates import (
    get_active_practicum_templates,
    get_practicum_template,
)

router = APIRouter()


def _sync_templates(db: Session) -> None:
    changed = False
    for definition in get_active_practicum_templates():
        template = db.scalar(
            select(PracticumTemplate).where(
                PracticumTemplate.slug == definition["slug"],
                PracticumTemplate.version == definition["version"],
            )
        )
        if template is None:
            template = PracticumTemplate(
                slug=definition["slug"],
                version=definition["version"],
                title=definition["title"],
                description=definition["description"],
                estimated_minutes=definition["estimated_minutes"],
                prerequisite_lesson_slugs=definition["prerequisite_lesson_slugs"],
                status=definition["status"],
            )
            db.add(template)
            db.flush()
            changed = True
        existing_keys = set(
            db.scalars(
                select(PracticumObjective.objective_key).where(
                    PracticumObjective.template_id == template.id
                )
            ).all()
        )
        for objective in definition["objectives"]:
            if objective["objective_key"] in existing_keys:
                continue
            db.add(
                PracticumObjective(
                    template_id=template.id,
                    objective_key=objective["objective_key"],
                    sequence=objective["sequence"],
                    title=objective["title"],
                    description=objective["description"],
                    competency=objective["competency"],
                    required_evidence_categories=objective["required_evidence_categories"],
                    minimum_evidence_count=objective["minimum_evidence_count"],
                    reflection_required=objective["reflection_required"],
                    human_review_required=objective["human_review_required"],
                )
            )
            changed = True
    if changed:
        db.commit()


def _template_read(db: Session, template: PracticumTemplate) -> PracticumTemplateRead:
    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == template.id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    return PracticumTemplateRead(
        id=template.id,
        slug=template.slug,
        version=template.version,
        title=template.title,
        description=template.description,
        estimated_minutes=template.estimated_minutes,
        prerequisite_lesson_slugs=template.prerequisite_lesson_slugs,
        status=template.status,
        objectives=objectives,
    )


def _owned_enrollment(db: Session, user_id: int, enrollment_id: int) -> PracticumEnrollment:
    enrollment = db.scalar(
        select(PracticumEnrollment).where(
            PracticumEnrollment.id == enrollment_id,
            PracticumEnrollment.user_id == user_id,
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum enrollment not found")
    return enrollment


def _enrollment_read(db: Session, enrollment: PracticumEnrollment) -> PracticumEnrollmentRead:
    template = db.get(PracticumTemplate, enrollment.template_id)
    progress_rows = list(
        db.scalars(
            select(PracticumObjectiveProgress)
            .where(PracticumObjectiveProgress.enrollment_id == enrollment.id)
            .order_by(PracticumObjectiveProgress.objective_key)
        ).all()
    )
    reviews = list(
        db.scalars(
            select(PracticumReviewDecision)
            .where(PracticumReviewDecision.enrollment_id == enrollment.id)
            .order_by(PracticumReviewDecision.created_at, PracticumReviewDecision.id)
        ).all()
    )
    return PracticumEnrollmentRead(
        id=enrollment.id,
        user_id=enrollment.user_id,
        template_slug=template.slug,
        template_version=enrollment.template_version,
        research_project_id=enrollment.research_project_id,
        status=enrollment.status,
        started_at=enrollment.started_at,
        submitted_for_review_at=enrollment.submitted_for_review_at,
        completed_at=enrollment.completed_at,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
        objectives=[
            PracticumObjectiveProgressRead(
                objective_key=row.objective_key,
                reflection=row.reflection,
                evidence_references=[],
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in progress_rows
        ],
        review_history=reviews,
    )


@router.get("/templates", response_model=list[PracticumTemplateRead])
def list_practicum_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PracticumTemplateRead]:
    del current_user
    _sync_templates(db)
    templates = list(
        db.scalars(
            select(PracticumTemplate)
            .where(PracticumTemplate.status == "active")
            .order_by(PracticumTemplate.slug, PracticumTemplate.version)
        ).all()
    )
    return [_template_read(db, template) for template in templates]


@router.get("/templates/{template_slug}", response_model=PracticumTemplateRead)
def get_practicum_template_route(
    template_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumTemplateRead:
    del current_user
    _sync_templates(db)
    template = db.scalar(
        select(PracticumTemplate)
        .where(PracticumTemplate.slug == template_slug, PracticumTemplate.status == "active")
        .order_by(PracticumTemplate.version.desc())
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum template not found")
    return _template_read(db, template)


@router.post("/enrollments", response_model=PracticumEnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_practicum_enrollment(
    payload: PracticumEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumEnrollmentRead:
    definition = get_practicum_template(payload.template_slug)
    if definition is None or definition["status"] != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum template not found")
    _sync_templates(db)
    template = db.scalar(
        select(PracticumTemplate).where(
            PracticumTemplate.slug == definition["slug"],
            PracticumTemplate.version == definition["version"],
        )
    )
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == payload.research_project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research project not found")

    completed_slugs = set(
        db.scalars(
            select(LessonProgress.lesson_slug).where(
                LessonProgress.user_id == current_user.id,
                LessonProgress.status == "completed",
            )
        ).all()
    )
    missing = [slug for slug in definition["prerequisite_lesson_slugs"] if slug not in completed_slugs]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Practicum prerequisites are incomplete", "missing_lesson_slugs": missing},
        )

    now = datetime.utcnow()
    enrollment = PracticumEnrollment(
        user_id=current_user.id,
        template_id=template.id,
        template_version=template.version,
        research_project_id=project.id,
        status="in_progress",
        started_at=now,
    )
    db.add(enrollment)
    try:
        db.flush()
        objectives = list(
            db.scalars(
                select(PracticumObjective)
                .where(PracticumObjective.template_id == template.id)
                .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
            ).all()
        )
        for objective in objectives:
            db.add(
                PracticumObjectiveProgress(
                    enrollment_id=enrollment.id,
                    objective_key=objective.objective_key,
                )
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum enrollment already exists") from exc
    db.refresh(enrollment)
    return _enrollment_read(db, enrollment)


@router.get("/enrollments", response_model=list[PracticumEnrollmentRead])
def list_practicum_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PracticumEnrollmentRead]:
    enrollments = list(
        db.scalars(
            select(PracticumEnrollment)
            .where(PracticumEnrollment.user_id == current_user.id)
            .order_by(PracticumEnrollment.created_at.desc(), PracticumEnrollment.id.desc())
        ).all()
    )
    return [_enrollment_read(db, enrollment) for enrollment in enrollments]


@router.get("/enrollments/{enrollment_id}", response_model=PracticumEnrollmentRead)
def get_practicum_enrollment(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumEnrollmentRead:
    return _enrollment_read(db, _owned_enrollment(db, current_user.id, enrollment_id))


@router.patch(
    "/enrollments/{enrollment_id}/objectives/{objective_key}",
    response_model=PracticumEnrollmentRead,
)
def update_practicum_objective(
    enrollment_id: int,
    objective_key: str,
    payload: PracticumObjectiveProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumEnrollmentRead:
    enrollment = _owned_enrollment(db, current_user.id, enrollment_id)
    if enrollment.status in {"review_ready", "completed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submitted practica cannot be edited")
    progress = db.scalar(
        select(PracticumObjectiveProgress).where(
            PracticumObjectiveProgress.enrollment_id == enrollment.id,
            PracticumObjectiveProgress.objective_key == objective_key,
        )
    )
    if progress is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum objective not found")
    progress.reflection = payload.reflection.strip() if payload.reflection else None
    enrollment.status = "in_progress"
    db.commit()
    db.refresh(enrollment)
    return _enrollment_read(db, enrollment)
