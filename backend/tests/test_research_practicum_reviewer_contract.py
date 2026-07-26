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


def test_reviewer_route_contract_enforces_authorization_filters_and_stale_decisions():
    root = Path(__file__).parents[1]
    route = (root / "app" / "api" / "routes" / "research_practicum_reviews.py").read_text(
        encoding="utf-8"
    )
    router = (root / "app" / "api" / "router.py").read_text(encoding="utf-8")

    assert "if not user.is_superuser" in route
    assert '@router.get("/queue"' in route
    assert "PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)" in route
    assert "PracticumTemplate.slug == template_slug" in route
    assert "PracticumEnrollment.user_id == learner_user_id" in route
    assert "submitted_for_review_at.asc().nulls_last()" in route
    assert ".offset((page - 1) * page_size)" in route
    assert '@router.get("/enrollments/{enrollment_id}"' in route
    assert 'record_source: Literal["measured_research_record"]' in (
        root / "app" / "schemas" / "research_practicum.py"
    ).read_text(encoding="utf-8")
    assert "expected_enrollment_updated_at" in route
    assert "Practicum changed after the reviewer loaded it" in route
    assert "PracticumReviewDecision(" in route
    assert "enrollment.status = \"completed\"" in route
    assert "enrollment.status = \"revision_required\"" in route
    assert "research_practicum_reviews.router" in router
    assert 'prefix="/education/practica/reviewer"' in router


def test_reviewer_detail_keeps_completed_decisions_readable_but_out_of_queue():
    route = (
        Path(__file__).parents[1] / "app" / "api" / "routes" / "research_practicum_reviews.py"
    ).read_text(encoding="utf-8")

    assert 'REVIEWABLE_STATUSES = {"review_ready", "revision_required"}' in route
    assert 'REVIEW_DETAIL_STATUSES = REVIEWABLE_STATUSES | {"completed"}' in route
    assert "PracticumEnrollment.status.in_(REVIEWABLE_STATUSES)" in route
    assert "enrollment.status not in REVIEW_DETAIL_STATUSES" in route
