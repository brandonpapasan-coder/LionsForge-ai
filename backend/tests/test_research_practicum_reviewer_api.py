from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.api.deps import get_current_user
from app.api.routes import research_practicum_reviews
from app.db.session import get_db
from app.main import app

NOW = datetime(2026, 7, 27, 1, 0, tzinfo=timezone.utc)
BASE = "/api/v1/education/practica/reviewer"


def _reviewer(*, superuser: bool = True):
    return SimpleNamespace(id=91, is_superuser=superuser)


def _queue_item(*, enrollment_id: int = 10, enrollment_status: str = "review_ready") -> dict:
    return {
        "enrollment_id": enrollment_id,
        "learner_user_id": 7,
        "learner_display_name": "Ada Learner",
        "template_slug": "evidence-validation-practicum",
        "template_title": "Evidence Validation Practicum",
        "template_version": 1,
        "research_project_id": 22,
        "research_project_title": "Measured Research Project",
        "status": enrollment_status,
        "submitted_for_review_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        "latest_review_decision": None,
    }


def _detail(*, enrollment_status: str = "review_ready", history: list[dict] | None = None) -> dict:
    return {
        "enrollment": _queue_item(enrollment_status=enrollment_status),
        "objectives": [],
        "readiness": {
            "enrollment_id": 10,
            "enrollment_status": enrollment_status,
            "advisory_notice": "Deterministic readiness is advisory and human review is required.",
            "objectives": [],
            "missing_requirements": [],
            "ready_for_human_review": True,
            "latest_review_decision": history[-1] if history else None,
        },
        "review_history": history or [],
        "advisory_notice": "Deterministic readiness is advisory and human review is required.",
    }


@pytest.fixture(autouse=True)
def reviewer_dependencies():
    app.dependency_overrides[get_current_user] = lambda: _reviewer()
    app.dependency_overrides[get_db] = lambda: object()
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_reviewer_endpoints_deny_non_superusers(client):
    app.dependency_overrides[get_current_user] = lambda: _reviewer(superuser=False)

    response = client.get(f"{BASE}/queue")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Practicum reviewer authorization required"


def test_queue_executes_filters_pagination_and_deterministic_contract(client, monkeypatch):
    captured: dict = {}

    def fake_list_queue(db, **kwargs):
        captured.update(kwargs)
        return {
            "items": [_queue_item()],
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total_items": 1,
            "total_pages": 1,
        }

    monkeypatch.setattr(research_practicum_reviews.reviewer_service, "list_queue", fake_list_queue)
    response = client.get(
        f"{BASE}/queue",
        params={
            "status": "review_ready",
            "template_slug": "evidence-validation-practicum",
            "learner_user_id": 7,
            "learner_query": "Ada",
            "submitted_from": "2026-07-01T00:00:00Z",
            "submitted_to": "2026-07-31T23:59:59Z",
            "page": 2,
            "page_size": 10,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["learner_display_name"] == "Ada Learner"
    assert captured["queue_status"] == "review_ready"
    assert captured["template_slug"] == "evidence-validation-practicum"
    assert captured["learner_user_id"] == 7
    assert captured["learner_query"] == "Ada"
    assert captured["page"] == 2
    assert captured["page_size"] == 10
    assert captured["submitted_from"] < captured["submitted_to"]


def test_completed_detail_remains_readable_outside_active_queue(client, monkeypatch):
    monkeypatch.setattr(
        research_practicum_reviews.reviewer_service,
        "get_detail",
        lambda db, enrollment_id: _detail(enrollment_status="completed"),
    )

    response = client.get(f"{BASE}/enrollments/10")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["enrollment"]["status"] == "completed"
    assert response.json()["human_review_required"] is True


def test_decision_endpoint_preserves_history_and_propagates_stale_conflicts(client, monkeypatch):
    history = [
        {
            "id": 31,
            "reviewer_user_id": 91,
            "decision": "revision_required",
            "notes": "Strengthen source provenance.",
            "created_at": NOW.isoformat(),
        }
    ]
    captured: dict = {}

    def fake_record_decision(db, *, enrollment_id, reviewer, payload):
        captured.update(
            enrollment_id=enrollment_id,
            reviewer_id=reviewer.id,
            decision=payload.decision,
            notes=payload.notes,
            expected=payload.expected_enrollment_updated_at,
        )
        return _detail(enrollment_status="revision_required", history=history)

    monkeypatch.setattr(
        research_practicum_reviews.reviewer_service,
        "record_decision",
        fake_record_decision,
    )
    response = client.post(
        f"{BASE}/enrollments/10/decision",
        json={
            "decision": "revision_required",
            "notes": "Strengthen source provenance.",
            "expected_enrollment_updated_at": NOW.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["review_history"] == history
    assert captured == {
        "enrollment_id": 10,
        "reviewer_id": 91,
        "decision": "revision_required",
        "notes": "Strengthen source provenance.",
        "expected": NOW,
    }

    def stale(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practicum changed after the reviewer loaded it",
        )

    monkeypatch.setattr(
        research_practicum_reviews.reviewer_service,
        "record_decision",
        stale,
    )
    stale_response = client.post(
        f"{BASE}/enrollments/10/decision",
        json={"decision": "approved", "expected_enrollment_updated_at": NOW.isoformat()},
    )

    assert stale_response.status_code == status.HTTP_409_CONFLICT
    assert stale_response.json()["detail"] == "Practicum changed after the reviewer loaded it"
