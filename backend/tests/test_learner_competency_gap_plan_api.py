from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import learner_competency_gap_plan as gap_plan_routes
from app.db.session import get_db
from app.main import app
from app.models.user import User


class DummyDb:
    pass


def _user() -> User:
    return User(id=51, email="learner@example.com", hashed_password="x", is_active=True, is_superuser=False)


def test_gap_plan_route_forwards_authenticated_learner(monkeypatch):
    captured = {}

    def fake_export(db, *, user, generated_at=None):
        captured.update({"db": db, "user_id": user.id, "generated_at": generated_at})
        return {
            "plan": {"learner_user_id": user.id, "recommendations": []},
            "receipt": {"plan_sha256": "a" * 64},
            "source_portfolio": {"portfolio_sha256": "b" * 64, "excluded_record_count": 0},
        }

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: DummyDb()
    monkeypatch.setattr(gap_plan_routes, "export_competency_gap_plan", fake_export)
    try:
        response = TestClient(app).get("/api/v1/education/competency-gap-plan")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["plan"]["learner_user_id"] == 51
    assert captured["user_id"] == 51
    assert isinstance(captured["db"], DummyDb)


def test_gap_plan_validation_route_returns_deterministic_findings(monkeypatch):
    app.dependency_overrides[get_current_user] = _user
    monkeypatch.setattr(
        gap_plan_routes,
        "validate_competency_gap_plan_bundle",
        lambda payload: {"valid": False, "findings": ["plan digest mismatch"]},
    )
    try:
        response = TestClient(app).post(
            "/api/v1/education/competency-gap-plan/validate",
            json={"plan": {}, "receipt": {}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"valid": False, "findings": ["plan digest mismatch"]}


def test_gap_plan_routes_are_registered_in_openapi():
    paths = app.openapi()["paths"]
    assert "/api/v1/education/competency-gap-plan" in paths
    assert "/api/v1/education/competency-gap-plan/validate" in paths


def test_gap_plan_export_uses_verified_owner_portfolio_and_bounded_active_catalog():
    source = Path("app/services/learner_competency_gap_plan_export.py").read_text()
    assert "export_competency_portfolio(db, user=user" in source
    assert 'PracticumTemplate.status == "active"' in source
    assert ".limit(MAX_ACTIVE_TEMPLATES)" in source
    assert 'PracticumEnrollment.user_id == user.id' in source
    assert 'PracticumEnrollment.status == "completed"' in source
    assert 'portfolio_receipt["portfolio_sha256"]' in source
    assert '"excluded_record_count": portfolio["excluded_record_count"]' in source
