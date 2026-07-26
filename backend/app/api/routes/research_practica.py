from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.education import LessonProgress
from app.models.research_evidence import ResearchEvidence
from app.models.research_practicum import (
    PracticumEnrollment,
    PracticumEvidenceReference,
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
    PracticumEvidenceReferenceCreate,
    PracticumEvidenceReferenceRead,
    PracticumObjectiveProgressRead,
    PracticumObjectiveProgressUpdate,
    PracticumObjectiveReadinessRead,
    PracticumReadinessRead,
    PracticumReviewDecisionCreate,
    PracticumReviewDecisionRead,
    PracticumTemplateRead,
)
from app.services.research_practicum_templates import (
    get_active_practicum_templates,
    get_practicum_template,
)

router = APIRouter()
ADVISORY_NOTICE = (
    "This readiness result is a deterministic workflow evaluation based on linked records. "
    "It is not accreditation, licensing, professional certification, or autonomous competency approval."
)


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


def _reviewable_enrollment(db: Session, reviewer: User, enrollment_id: int) -> PracticumEnrollment:
    if not reviewer.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Practicum reviewer authorization required")
    enrollment = db.get(PracticumEnrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum enrollment not found")
    return enrollment


def _progress_rows(db: Session, enrollment_id: int) -> list[PracticumObjectiveProgress]:
    return list(
        db.scalars(
            select(PracticumObjectiveProgress)
            .where(PracticumObjectiveProgress.enrollment_id == enrollment_id)
            .order_by(PracticumObjectiveProgress.objective_key)
        ).all()
    )


def _review_read(row: PracticumReviewDecision) -> PracticumReviewDecisionRead:
    return PracticumReviewDecisionRead(
        id=row.id,
        reviewer_user_id=row.reviewer_user_id,
        decision=row.decision,
        notes=row.notes,
        created_at=row.created_at,
    )


def _enrollment_read(db: Session, enrollment: PracticumEnrollment) -> PracticumEnrollmentRead:
    template = db.get(PracticumTemplate, enrollment.template_id)
    progress_rows = _progress_rows(db, enrollment.id)
    progress_ids = [row.id for row in progress_rows]
    references = (
        list(
            db.scalars(
                select(PracticumEvidenceReference)
                .where(PracticumEvidenceReference.objective_progress_id.in_(progress_ids))
                .order_by(PracticumEvidenceReference.created_at, PracticumEvidenceReference.id)
            ).all()
        )
        if progress_ids
        else []
    )
    references_by_progress: dict[int, list[PracticumEvidenceReferenceRead]] = {}
    for reference in references:
        references_by_progress.setdefault(reference.objective_progress_id, []).append(
            PracticumEvidenceReferenceRead(
                id=reference.id,
                research_evidence_id=reference.research_evidence_id,
                created_at=reference.created_at,
            )
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
                evidence_references=references_by_progress.get(row.id, []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in progress_rows
        ],
        review_history=[_review_read(row) for row in reviews],
    )


def _readiness(db: Session, enrollment: PracticumEnrollment) -> PracticumReadinessRead:
    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == enrollment.template_id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    progress_by_key = {row.objective_key: row for row in _progress_rows(db, enrollment.id)}
    latest_review = db.scalar(
        select(PracticumReviewDecision)
        .where(PracticumReviewDecision.enrollment_id == enrollment.id)
        .order_by(PracticumReviewDecision.created_at.desc(), PracticumReviewDecision.id.desc())
    )
    objective_results: list[PracticumObjectiveReadinessRead] = []
    overall_missing: list[str] = []
    approved = latest_review is not None and latest_review.decision == "approved"

    for objective in objectives:
        progress = progress_by_key[objective.objective_key]
        references = list(
            db.scalars(
                select(PracticumEvidenceReference)
                .where(PracticumEvidenceReference.objective_progress_id == progress.id)
                .order_by(PracticumEvidenceReference.research_evidence_id)
            ).all()
        )
        evidence_ids = [reference.research_evidence_id for reference in references]
        evidence_rows = (
            list(db.scalars(select(ResearchEvidence).where(ResearchEvidence.id.in_(evidence_ids))).all())
            if evidence_ids
            else []
        )
        categories = sorted({evidence.source_type for evidence in evidence_rows})
        missing: list[str] = []
        if len(evidence_ids) < objective.minimum_evidence_count:
            missing.append(f"At least {objective.minimum_evidence_count} evidence reference(s) are required.")
        for category in objective.required_evidence_categories:
            if category not in categories:
                missing.append(f"Evidence category '{category}' is required.")
        reflection_present = bool(progress.reflection and progress.reflection.strip())
        if objective.reflection_required and not reflection_present:
            missing.append("A learner-authored reflection is required.")
        if missing:
            objective_status = "missing_requirements"
            overall_missing.extend(f"{objective.objective_key}: {item}" for item in missing)
        elif approved:
            objective_status = "approved"
        else:
            objective_status = "ready_for_review"
        objective_results.append(
            PracticumObjectiveReadinessRead(
                objective_key=objective.objective_key,
                sequence=objective.sequence,
                competency=objective.competency,
                status=objective_status,
                referenced_evidence_ids=evidence_ids,
                covered_evidence_categories=categories,
                reflection_present=reflection_present,
                human_review_required=objective.human_review_required,
                missing_requirements=missing,
            )
        )

    ready = not overall_missing
    return PracticumReadinessRead(
        enrollment_id=enrollment.id,
        enrollment_status=enrollment.status,
        advisory_notice=ADVISORY_NOTICE,
        objectives=objective_results,
        missing_requirements=overall_missing,
        ready_for_human_review=ready,
        latest_review_decision=_review_read(latest_review) if latest_review else None,
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
    enrollment = PracticumEnrollment(
        user_id=current_user.id,
        template_id=template.id,
        template_version=template.version,
        research_project_id=project.id,
        status="in_progress",
        started_at=datetime.utcnow(),
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
            db.add(PracticumObjectiveProgress(enrollment_id=enrollment.id, objective_key=objective.objective_key))
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


@router.patch("/enrollments/{enrollment_id}/objectives/{objective_key}", response_model=PracticumEnrollmentRead)
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


@router.post(
    "/enrollments/{enrollment_id}/objectives/{objective_key}/evidence",
    response_model=PracticumEnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
def attach_practicum_evidence(
    enrollment_id: int,
    objective_key: str,
    payload: PracticumEvidenceReferenceCreate,
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
    evidence = db.scalar(
        select(ResearchEvidence)
        .join(ResearchProject, ResearchProject.id == ResearchEvidence.project_id)
        .where(
            ResearchEvidence.id == payload.research_evidence_id,
            ResearchEvidence.project_id == enrollment.research_project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if progress is None or evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum objective or evidence not found")
    db.add(
        PracticumEvidenceReference(
            objective_progress_id=progress.id,
            research_evidence_id=evidence.id,
        )
    )
    try:
        enrollment.status = "in_progress"
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Evidence is already attached") from exc
    db.refresh(enrollment)
    return _enrollment_read(db, enrollment)


@router.delete(
    "/enrollments/{enrollment_id}/objectives/{objective_key}/evidence/{reference_id}",
    response_model=PracticumEnrollmentRead,
)
def remove_practicum_evidence(
    enrollment_id: int,
    objective_key: str,
    reference_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumEnrollmentRead:
    enrollment = _owned_enrollment(db, current_user.id, enrollment_id)
    if enrollment.status in {"review_ready", "completed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submitted practica cannot be edited")
    reference = db.scalar(
        select(PracticumEvidenceReference)
        .join(PracticumObjectiveProgress, PracticumObjectiveProgress.id == PracticumEvidenceReference.objective_progress_id)
        .where(
            PracticumEvidenceReference.id == reference_id,
            PracticumObjectiveProgress.enrollment_id == enrollment.id,
            PracticumObjectiveProgress.objective_key == objective_key,
        )
    )
    if reference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence reference not found")
    db.delete(reference)
    enrollment.status = "in_progress"
    db.commit()
    db.refresh(enrollment)
    return _enrollment_read(db, enrollment)


@router.get("/enrollments/{enrollment_id}/readiness", response_model=PracticumReadinessRead)
def get_practicum_readiness(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReadinessRead:
    return _readiness(db, _owned_enrollment(db, current_user.id, enrollment_id))


@router.post("/enrollments/{enrollment_id}/submit", response_model=PracticumReadinessRead)
def submit_practicum_for_review(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReadinessRead:
    enrollment = _owned_enrollment(db, current_user.id, enrollment_id)
    if enrollment.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed practica cannot be resubmitted")
    readiness = _readiness(db, enrollment)
    if not readiness.ready_for_human_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Practicum is not ready for review", "missing_requirements": readiness.missing_requirements},
        )
    enrollment.status = "review_ready"
    enrollment.submitted_for_review_at = datetime.utcnow()
    db.commit()
    db.refresh(enrollment)
    return _readiness(db, enrollment)


@router.post("/enrollments/{enrollment_id}/reviews", response_model=PracticumReadinessRead)
def review_practicum(
    enrollment_id: int,
    payload: PracticumReviewDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReadinessRead:
    enrollment = _reviewable_enrollment(db, current_user, enrollment_id)
    if enrollment.status != "review_ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum is not awaiting review")
    readiness = _readiness(db, enrollment)
    if not readiness.ready_for_human_review:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum requirements are incomplete")
    decision = PracticumReviewDecision(
        enrollment_id=enrollment.id,
        reviewer_user_id=current_user.id,
        decision=payload.decision,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(decision)
    if payload.decision == "approved":
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
    else:
        enrollment.status = "revision_required"
        enrollment.completed_at = None
    db.commit()
    db.refresh(enrollment)
    return _readiness(db, enrollment)
