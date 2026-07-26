from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.research_practicum import (
    PracticumReviewDecisionCreate,
    PracticumReviewerQueueRead,
)


def test_revision_decision_requires_reviewer_notes():
    with pytest.raises(ValidationError, match="Reviewer notes are required"):
        PracticumReviewDecisionCreate(decision="revision_required")

    payload = PracticumReviewDecisionCreate(
        decision="revision_required",
        notes="Add one independently sourced record and explain the conflict.",
    )

    assert payload.notes is not None


def test_approval_can_be_recorded_without_notes_and_with_stale_guard():
    expected_updated_at = datetime.now(UTC)

    payload = PracticumReviewDecisionCreate(
        decision="approved",
        expected_enrollment_updated_at=expected_updated_at,
    )

    assert payload.notes is None
    assert payload.expected_enrollment_updated_at == expected_updated_at


def test_reviewer_queue_pagination_bounds_are_enforced():
    queue = PracticumReviewerQueueRead(
        items=[],
        page=1,
        page_size=25,
        total_items=0,
        total_pages=0,
    )

    assert queue.items == []

    with pytest.raises(ValidationError):
        PracticumReviewerQueueRead(
            items=[],
            page=0,
            page_size=101,
            total_items=0,
            total_pages=0,
        )
