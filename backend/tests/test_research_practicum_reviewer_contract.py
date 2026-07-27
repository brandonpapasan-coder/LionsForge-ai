from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.research_practicum import (
    PracticumReviewDecisionCreate,
    PracticumReviewerQueueRead,
)


def test_revision_decision_requires_reviewer_notes():
    with pytest.raises(ValidationError):
        PracticumReviewDecisionCreate(decision="revision_required", notes="   ")


def test_approval_may_omit_reviewer_notes():
    payload = PracticumReviewDecisionCreate(decision="approved")

    assert payload.notes is None
    assert payload.expected_enrollment_updated_at is None


def test_reviewer_decision_accepts_stale_guard_timestamp():
    expected = datetime(2026, 7, 26, 12, 30)
    payload = PracticumReviewDecisionCreate(
        decision="revision_required",
        notes="Clarify the evidence-to-claim connection.",
        expected_enrollment_updated_at=expected,
    )

    assert payload.expected_enrollment_updated_at == expected


def test_reviewer_queue_pagination_is_bounded():
    with pytest.raises(ValidationError):
        PracticumReviewerQueueRead(
            items=[],
            page=1,
            page_size=101,
            total_items=0,
            total_pages=0,
        )


def test_reviewer_routes_delegate_to_dedicated_service_without_private_route_helpers():
    root = Path(__file__).parents[1]
    route = (root / "app" / "api" / "routes" / "research_practicum_reviews.py").read_text(
        encoding="utf-8"
    )
    service = (root / "app" / "services" / "research_practicum_reviewer.py").read_text(
        encoding="utf-8"
    )
    router = (root / "app" / "api" / "router.py").read_text(encoding="utf-8")

    assert "from app.api.routes.research_practica import" not in route
    assert "_readiness" not in route
    assert "_review_read" not in route
    assert "from app.services.research_practicum_reviewer import" in route
    assert "return list_queue(" in route
    assert "return get_detail(db, enrollment_id)" in route
    assert "return record_decision(" in route

    assert "if not user.is_superuser" in service
    assert 'REVIEWABLE_STATUSES = {"review_ready", "revision_required"}' in service
    assert 'REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}' in service
    assert "PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)" in service
    assert "PracticumTemplate.slug == template_slug" in service
    assert "PracticumEnrollment.user_id == learner_user_id" in service
    assert "func.lower(func.coalesce(User.full_name" in service
    assert "func.lower(User.email).like(pattern)" in service
    assert "submitted_for_review_at.asc().nulls_last()" in service
    assert ".offset((page - 1) * page_size)" in service
    assert ".join(User, User.id == PracticumEnrollment.user_id)" in service
    assert ".join(ResearchProject, ResearchProject.id == PracticumEnrollment.research_project_id)" in service
    assert "latest_review_id" in service
    assert "expected_enrollment_updated_at" in service
    assert "Practicum changed after the reviewer loaded it" in service
    assert "PracticumReviewDecision(" in service
    assert 'enrollment.status = "completed"' in service
    assert 'enrollment.status = "revision_required"' in service
    assert "review_history=[review_read(row) for row in history]" in service

    assert 'record_source: Literal["measured_research_record"]' in (
        root / "app" / "schemas" / "research_practicum.py"
    ).read_text(encoding="utf-8")
    assert "research_practicum_reviews.router" in router
    assert 'prefix="/education/practica/reviewer"' in router


def test_reviewer_detail_keeps_completed_decisions_readable_but_out_of_queue():
    service = (
        Path(__file__).parents[1] / "app" / "services" / "research_practicum_reviewer.py"
    ).read_text(encoding="utf-8")

    assert 'REVIEWABLE_STATUSES = {"review_ready", "revision_required"}' in service
    assert 'REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}' in service
    assert "PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)" in service
    assert "enrollment.status not in REVIEW_DETAIL_STATUSES" in service
