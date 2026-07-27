from datetime import datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import research_practicum_legacy_reviews as legacy_route
from app.db.session import get_db
from app.schemas.research_practicum import PracticumReadinessRead


def _readiness() -> PracticumReadinessRead:
    return PracticumReadinessRead(
        enrollment_id=41,
        enrollment_status="revision_required",
        advisory_notice="Deterministic readiness is advisory and requires human review.",
        objectives=[],
        missing_requirements=[],
        ready_for_human_review=True,
        latest_review_decision=None,
    )


def _client(user: SimpleNamespace) -> TestClient:
    app = FastAPI()
    app.include_router(legacy_route.router, prefix="/api/v1/education/practica")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: object()
    return TestClient(app)


def test_legacy_review_endpoint_delegates_to_canonical_service(monkeypatch):
    reviewer = SimpleNamespace(id=7, is_superuser=True)
    expected = datetime(2026, 7, 27, 1, 15)
    captured = {}

    def record_decision(db, *, enrollment_id, reviewer, payload):
        captured.update(
            db=db,
            enrollment_id=enrollment_id,
            reviewer_id=reviewer.id,
            decision=payload.decision,
            notes=payload.notes,
            expected=payload.expected_enrollment_updated_at,
        )
        return SimpleNamespace(readiness=_readiness())

    monkeypatch.setattr(legacy_route.reviewer_service, "record_decision", record_decision)

    response = _client(reviewer).post(
        "/api/v1/education/practica/enrollments/41/reviews",
        json={
            "decision": "revision_required",
            "notes": "Add stronger source provenance.",
            "expected_enrollment_updated_at": expected.isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["enrollment_status"] == "revision_required"
    assert captured == {
        "db": captured["db"],
        "enrollment_id": 41,
        "reviewer_id": 7,
        "decision": "revision_required",
        "notes": "Add stronger source provenance.",
        "expected": expected,
    }


def test_legacy_review_endpoint_preserves_reviewer_authorization():
    response = _client(SimpleNamespace(id=8, is_superuser=False)).post(
        "/api/v1/education/practica/enrollments/41/reviews",
        json={"decision": "approved"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Practicum reviewer authorization required"
