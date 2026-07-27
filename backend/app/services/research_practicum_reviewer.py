from datetime import datetime
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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
    PracticumObjectiveReadinessRead,
    PracticumReadinessRead,
    PracticumReviewDecisionCreate,
    PracticumReviewDecisionRead,
    PracticumReviewerDetailRead,
    PracticumReviewerEvidenceRead,
    PracticumReviewerObjectiveRead,
    PracticumReviewerQueueItemRead,
    PracticumReviewerQueueRead,
)

ADVISORY_NOTICE = (
    "This readiness result is a deterministic workflow evaluation based on linked records. "
    "It is not accreditation, licensing, professional certification, or autonomous competency approval."
)
REVIEWABLE_STATUSES = {"review_ready", "revision_required"}
REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}


def require_reviewer(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Practicum reviewer authorization required",
        )


def serialize_review_decision(row: PracticumReviewDecision) -> PracticumReviewDecisionRead:
    return PracticumReviewDecisionRead(
        id=row.id,
        reviewer_user_id=row.reviewer_user_id,
        decision=row.decision,
        notes=row.notes,
        created_at=row.created_at,
    )


def _progress_rows(db: Session, enrollment_id: int) -> list[PracticumObjectiveProgress]:
    return list(
        db.scalars(
            select(PracticumObjectiveProgress)
            .where(PracticumObjectiveProgress.enrollment_id == enrollment_id)
            .order_by(PracticumObjectiveProgress.objective_key)
        ).all()
    )


def build_practicum_readiness(db: Session, enrollment: PracticumEnrollment) -> PracticumReadinessRead:
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

    return PracticumReadinessRead(
        enrollment_id=enrollment.id,
        enrollment_status=enrollment.status,
        advisory_notice=ADVISORY_NOTICE,
        objectives=objective_results,
        missing_requirements=overall_missing,
        ready_for_human_review=not overall_missing,
        latest_review_decision=serialize_review_decision(latest_review) if latest_review else None,
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
        latest_review_decision=serialize_review_decision(latest_review) if latest_review else None,
    )


def _latest_review_id_subquery():
    return (
        select(PracticumReviewDecision.id)
        .where(PracticumReviewDecision.enrollment_id == PracticumEnrollment.id)
        .order_by(PracticumReviewDecision.created_at.desc(), PracticumReviewDecision.id.desc())
        .limit(1)
        .correlate(PracticumEnrollment)
        .scalar_subquery()
    )


def list_reviewer_queue(
    db: Session,
    *,
    queue_status: str | None,
    template_slug: str | None,
    learner_user_id: int | None,
    learner_query: str | None,
    submitted_from: datetime | None,
    submitted_to: datetime | None,
    page: int,
    page_size: int,
) -> PracticumReviewerQueueRead:
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

    base = (
        select(PracticumEnrollment, User, PracticumTemplate, ResearchProject, PracticumReviewDecision)
        .join(User, User.id == PracticumEnrollment.user_id)
        .join(PracticumTemplate, PracticumTemplate.id == PracticumEnrollment.template_id)
        .join(ResearchProject, ResearchProject.id == PracticumEnrollment.research_project_id)
        .outerjoin(PracticumReviewDecision, PracticumReviewDecision.id == _latest_review_id_subquery())
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


def get_reviewable_enrollment(db: Session, enrollment_id: int) -> PracticumEnrollment:
    enrollment = db.get(PracticumEnrollment, enrollment_id)
    if enrollment is None or enrollment.status not in REVIEW_DETAIL_STATUSES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewable practicum not found")
    return enrollment


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


def build_reviewer_detail(db: Session, enrollment: PracticumEnrollment) -> PracticumReviewerDetailRead:
    readiness = build_practicum_readiness(db, enrollment)
    readiness_by_key = {item.objective_key: item for item in readiness.objectives}
    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == enrollment.template_id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    progress_rows = list(
        db.scalars(select(PracticumObjectiveProgress).where(PracticumObjectiveProgress.enrollment_id == enrollment.id)).all()
    )
    progress_by_key = {row.objective_key: row for row in progress_rows}
    reviewer_objectives: list[PracticumReviewerObjectiveRead] = []
    for objective in objectives:
        progress = progress_by_key[objective.objective_key]
        evidence_rows = list(
            db.scalars(
                select(ResearchEvidence)
                .join(PracticumEvidenceReference, PracticumEvidenceReference.research_evidence_id == ResearchEvidence.id)
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
        review_history=[serialize_review_decision(row) for row in review_history],
        advisory_notice=ADVISORY_NOTICE,
    )


def record_reviewer_decision(
    db: Session,
    *,
    enrollment: PracticumEnrollment,
    reviewer: User,
    payload: PracticumReviewDecisionCreate,
) -> PracticumReviewerDetailRead:
    if payload.expected_enrollment_updated_at and enrollment.updated_at != payload.expected_enrollment_updated_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum changed after the reviewer loaded it")
    if enrollment.status != "review_ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum must be resubmitted before a new decision")
    readiness = build_practicum_readiness(db, enrollment)
    if not readiness.ready_for_human_review:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum requirements are incomplete")
    db.add(
        PracticumReviewDecision(
            enrollment_id=enrollment.id,
            reviewer_user_id=reviewer.id,
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
    return build_reviewer_detail(db, enrollment)
