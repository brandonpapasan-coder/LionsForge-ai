from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.research_practicum import PracticumReviewDecisionCreate
from app.services import research_practicum_reviewer as reviewer_service


def test_require_reviewer_denies_non_superuser():
    with pytest.raises(HTTPException) as exc_info:
        reviewer_service.require_reviewer(SimpleNamespace(is_superuser=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Practicum reviewer authorization required"


def test_require_reviewer_accepts_superuser():
    reviewer_service.require_reviewer(SimpleNamespace(is_superuser=True))


def test_stale_decision_is_rejected_before_database_write():
    db = MagicMock()
    enrollment = SimpleNamespace(
        id=41,
        status="review_ready",
        updated_at=datetime(2026, 7, 27, 8, 0),
    )
    payload = PracticumReviewDecisionCreate(
        decision="approved",
        expected_enrollment_updated_at=enrollment.updated_at - timedelta(seconds=1),
    )

    with pytest.raises(HTTPException) as exc_info:
        reviewer_service.record_reviewer_decision(
            db,
            enrollment=enrollment,
            reviewer=SimpleNamespace(id=9),
            payload=payload,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Practicum changed after the reviewer loaded it"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_approval_records_human_reviewer_and_completes_enrollment(monkeypatch):
    db = MagicMock()
    enrollment = SimpleNamespace(
        id=42,
        status="review_ready",
        updated_at=datetime(2026, 7, 27, 8, 0),
        completed_at=None,
    )
    reviewer = SimpleNamespace(id=17)
    payload = PracticumReviewDecisionCreate(
        decision="approved",
        notes="Evidence and reflection satisfy the practicum requirements.",
        expected_enrollment_updated_at=enrollment.updated_at,
    )
    expected_detail = SimpleNamespace(enrollment=SimpleNamespace(status="completed"))
    monkeypatch.setattr(
        reviewer_service,
        "build_practicum_readiness",
        lambda _db, _enrollment: SimpleNamespace(ready_for_human_review=True),
    )
    monkeypatch.setattr(
        reviewer_service,
        "build_reviewer_detail",
        lambda _db, _enrollment: expected_detail,
    )

    result = reviewer_service.record_reviewer_decision(
        db,
        enrollment=enrollment,
        reviewer=reviewer,
        payload=payload,
    )

    decision = db.add.call_args.args[0]
    assert decision.enrollment_id == enrollment.id
    assert decision.reviewer_user_id == reviewer.id
    assert decision.decision == "approved"
    assert decision.notes == payload.notes
    assert enrollment.status == "completed"
    assert enrollment.completed_at is not None
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(enrollment)
    assert result is expected_detail


def test_revision_records_notes_and_requires_resubmission(monkeypatch):
    db = MagicMock()
    enrollment = SimpleNamespace(
        id=43,
        status="review_ready",
        updated_at=datetime(2026, 7, 27, 8, 0),
        completed_at=datetime(2026, 7, 26, 8, 0),
    )
    payload = PracticumReviewDecisionCreate(
        decision="revision_required",
        notes="Clarify how the cited evidence supports the central claim.",
        expected_enrollment_updated_at=enrollment.updated_at,
    )
    monkeypatch.setattr(
        reviewer_service,
        "build_practicum_readiness",
        lambda _db, _enrollment: SimpleNamespace(ready_for_human_review=True),
    )
    monkeypatch.setattr(
        reviewer_service,
        "build_reviewer_detail",
        lambda _db, _enrollment: SimpleNamespace(),
    )

    reviewer_service.record_reviewer_decision(
        db,
        enrollment=enrollment,
        reviewer=SimpleNamespace(id=18),
        payload=payload,
    )

    decision = db.add.call_args.args[0]
    assert decision.decision == "revision_required"
    assert decision.notes == payload.notes
    assert enrollment.status == "revision_required"
    assert enrollment.completed_at is None

    with pytest.raises(HTTPException) as exc_info:
        reviewer_service.record_reviewer_decision(
            MagicMock(),
            enrollment=enrollment,
            reviewer=SimpleNamespace(id=18),
            payload=payload,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Practicum must be resubmitted before a new decision"
