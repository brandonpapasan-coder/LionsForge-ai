from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.research_practica import ADVISORY_NOTICE, _readiness, _review_read
from app.db.session import get_db
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
    PracticumReviewDecisionCreate,
    PracticumReviewerDetailRead,
    PracticumReviewerEvidenceRead,
    PracticumReviewerObjectiveRead,
    PracticumReviewerQueueItemRead,
    PracticumReviewerQueueRead,
)

router = APIRouter()
REVIEWABLE_STATUSES = {"review_ready", "revision_required"}
REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}


def _require_reviewer(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Practicum reviewer authorization required",
        )


def _queue_item(
    enrollment: PracticumEnrollment,
    learner: User | None,
    template: PracticumTemplate,
    project: ResearchProject,
    latest_review: PracticumReviewDecision | None,
) -> PracticumReviewerQueueItemRead:
    return PracticumReviewerQueueItemRead(
        enrollment_id=enrollment.id,
        learner_user_id=enrollment.user_id,
        learner_display_name=(learner.full_name or learner.email) if learner else "Unknown learner",
        template_slug=template.slug,
        template_title=template.title,
        template_version=enrollment.template_version,
        research_project_id=enrollment.research_project_id,
        research_project_title=project.title,
        status=enrollment.status,
        submitted_for_review_at=enrollment.submitted_for_review_at,
        updated_at=enrollment.updated_at,
        latest_review_decision=_review_read(latest_review) if latest_review else None,
    )


def _queue_item_for_enrollment(db: Session, enrollment: PracticumEnrollment) -> PracticumReviewerQueueItemRead:
    learner = db.get(User, enrollment.user_id)
    template = db.get(PracticumTemplate, enrollment.template_id)
    project = db.get(ResearchProject, enrollment.research_project_id)
    latest_review = db.scalar(
        select(PracticumReviewDecision)
        .where(PracticumReviewDecision.enrollment_id == enrollment.id)
        .order_by(PracticumReviewDecision.created_at.desc(), PracticumReviewDecision.id.desc())
    )
    if template is None or project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum context not found")
    return _queue_item(enrollment, learner, template, project, latest_review)


def _detail_enrollment(db: Session, enrollment_id: int) -> PracticumEnrollment:
    enrollment = db.get(PracticumEnrollment, enrollment_id)
    if enrollment is None or enrollment.status not in REVIEW_DETAIL_STATUSES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewable practicum not found")
    return enrollment


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
    _require_reviewer(current_user)
    if queue_status is not None and queue_status not in REVIEWABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported queue status")
    if submitted_from and submitted_to and submitted_from > submitted_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid submission date range")

    filters = [PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)]
    if queue_status:
        filters.append(PracticumEnrollment.status == queue_status)
    if template_slug:
        filters.append(PracticumTemplate.slug == template_slug)
    if learner_user_id:
        filters.append(PracticumEnrollment.user_id == learner_user_id)
    if learner_query:
        normalized_query = learner_query.strip().lower()
        if normalized_query:
            pattern = f"%{normalized_query}%"
            filters.append(
                or_(
                    func.lower(func.coalesce(User.full_name, "")).like(pattern),
                    func.lower(User.email).like(pattern),
                )
            )
    if submitted_from:
        filters.append(PracticumEnrollment.submitted_for_review_at >= submitted_from)
    if submitted_to:
        filters.append(PracticumEnrollment.submitted_for_review_at <= submitted_to)

    latest_review_id = (
        select(PracticumReviewDecision.id)
        .where(PracticumReviewDecision.enrollment_id == PracticumEnrollment.id)
        .order_by(PracticumReviewDecision.created_at.desc(), PracticumReviewDecision.id.desc())
        .limit(1)
        .correlate(PracticumEnrollment)
        .scalar_subquery()
    )
    base = (
        select(PracticumEnrollment, User, PracticumTemplate, ResearchProject, PracticumReviewDecision)
        .join(User, User.id == PracticumEnrollment.user_id)
        .join(PracticumTemplate, PracticumTemplate.id == PracticumEnrollment.template_id)
        .join(ResearchProject, ResearchProject.id == PracticumEnrollment.research_project_id)
        .outerjoin(PracticumReviewDecision, PracticumReviewDecision.id == latest_review_id)
        .where(*filters)
    )
    total_items = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    rows = list(
        db.execute(
            base.order_by(
                PracticumEnrollment.submitted_for_review_at.asc().nulls_last(),
                PracticumEnrollment.updated_at.asc(),
                PracticumEnrollment.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PracticumReviewerQueueRead(
        items=[_queue_item(enrollment, learner, template, project, latest_review) for enrollment, learner, template, project, latest_review in rows],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=ceil(total_items / page_size) if total_items else 0,
    )


@router.get("/enrollments/{enrollment_id}", response_model=PracticumReviewerDetailRead)
def get_reviewer_detail(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReviewerDetailRead:
    _require_reviewer(current_user)
    enrollment = _detail_enrollment(db, enrollment_id)
    readiness = _readiness(db, enrollment)
    readiness_by_key = {item.objective_key: item for item in readiness.objectives}
    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == enrollment.template_id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    progress_rows = list(
        db.scalars(
            select(PracticumObjectiveProgress).where(
                PracticumObjectiveProgress.enrollment_id == enrollment.id
            )
        ).all()
    )
    progress_by_key = {row.objective_key: row for row in progress_rows}
    reviewer_objectives: list[PracticumReviewerObjectiveRead] = []
    for objective in objectives:
        progress = progress_by_key[objective.objective_key]
        evidence_rows = list(
            db.scalars(
                select(ResearchEvidence)
                .join(
                    PracticumEvidenceReference,
                    PracticumEvidenceReference.research_evidence_id == ResearchEvidence.id,
                )
                .where(
                    PracticumEvidenceReference.objective_progress_id == progress.id,
                    ResearchEvidence.project_id == enrollment.research_project_id,
                )
                .order_by(ResearchEvidence.created_at, ResearchEvidence.id)
            ).all()
        )
        reviewer_objectives.append(
            PracticumReviewerObjectiveRead(
                objective_key=objective.objective_key,
                sequence=objective.sequence,
                title=objective.title,
                description=objective.description,
                competency=objective.competency,
                reflection=progress.reflection,
                evidence=[
                    PracticumReviewerEvidenceRead(
                        id=evidence.id,
                        title=evidence.title,
                        summary=evidence.summary,
                        source_type=evidence.source_type,
                        status=evidence.status,
                        tags=evidence.tags,
                        created_at=evidence.created_at,
                        updated_at=evidence.updated_at,
                    )
                    for evidence in evidence_rows
                ],
                readiness=readiness_by_key[objective.objective_key],
            )
        )
    review_history = list(
        db.scalars(
            select(PracticumReviewDecision)
            .where(PracticumReviewDecision.enrollment_id == enrollment.id)
            .order_by(PracticumReviewDecision.created_at, PracticumReviewDecision.id)
        ).all()
    )
    return PracticumReviewerDetailRead(
        enrollment=_queue_item_for_enrollment(db, enrollment),
        objectives=reviewer_objectives,
        readiness=readiness,
        review_history=[_review_read(row) for row in review_history],
        advisory_notice=ADVISORY_NOTICE,
    )


@router.post("/enrollments/{enrollment_id}/decision", response_model=PracticumReviewerDetailRead)
def record_reviewer_decision(
    enrollment_id: int,
    payload: PracticumReviewDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticumReviewerDetailRead:
    _require_reviewer(current_user)
    enrollment = _detail_enrollment(db, enrollment_id)
    if payload.expected_enrollment_updated_at and enrollment.updated_at != payload.expected_enrollment_updated_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practicum changed after the reviewer loaded it",
        )
    if enrollment.status != "review_ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practicum must be resubmitted before a new decision",
        )
    readiness = _readiness(db, enrollment)
    if not readiness.ready_for_human_review:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum requirements are incomplete")
    db.add(
        PracticumReviewDecision(
            enrollment_id=enrollment.id,
            reviewer_user_id=current_user.id,
            decision=payload.decision,
            notes=payload.notes.strip() if payload.notes else None,
        )
    )
    if payload.decision == "approved":
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
    else:
        enrollment.status = "revision_required"
        enrollment.completed_at = None
    db.commit()
    db.refresh(enrollment)
    return get_reviewer_detail(enrollment.id, current_user, db)
