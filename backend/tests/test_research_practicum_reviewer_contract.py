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


def test_reviewer_routes_use_stable_service_boundary():
    root = Path(__file__).parents[1]
    route = (root / "app" / "api" / "routes" / "research_practicum_reviews.py").read_text(
        encoding="utf-8"
    )
    service = (root / "app" / "services" / "research_practicum_reviewer.py").read_text(
        encoding="utf-8"
    )
    router = (root / "app" / "api" / "router.py").read_text(encoding="utf-8")

    assert "from app.api.routes.research_practica import" not in route
    assert "from app.services.research_practicum_reviewer import" in route
    assert "require_reviewer(current_user)" in route
    assert "list_reviewer_queue_service(" in route
    assert "build_reviewer_detail(" in route
    assert "record_reviewer_decision_service(" in route
    assert '@router.get("/queue"' in route
    assert '@router.get("/enrollments/{enrollment_id}"' in route
    assert "PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)" in service
    assert "PracticumTemplate.slug == template_slug" in service
    assert "PracticumEnrollment.user_id == learner_user_id" in service
    assert "func.lower(func.coalesce(User.full_name" in service
    assert "func.lower(User.email).like(pattern)" in service
    assert "submitted_for_review_at.asc().nulls_last()" in service
    assert ".offset((page - 1) * page_size)" in service
    assert "Practicum changed after the reviewer loaded it" in service
    assert 'enrollment.status = "completed"' in service
    assert 'enrollment.status = "revision_required"' in service
    assert "research_practicum_reviews.router" in router
    assert 'prefix="/education/practica/reviewer"' in router


def test_reviewer_service_keeps_completed_details_outside_active_queue():
    service = (
        Path(__file__).parents[1] / "app" / "services" / "research_practicum_reviewer.py"
    ).read_text(encoding="utf-8")

    assert 'REVIEWABLE_STATUSES = {"review_ready", "revision_required"}' in service
    assert 'REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}' in service
    assert "enrollment.status not in REVIEW_DETAIL_STATUSES" in service
    assert "review_history=[serialize_review_decision(row) for row in review_history]" in service
