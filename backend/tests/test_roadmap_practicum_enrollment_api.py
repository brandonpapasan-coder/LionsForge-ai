from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import roadmap_practicum_enrollment as enrollment_routes
from app.db.session import get_db
from app.main import app
from app.models.user import User


class DummyDb:
    pass


def _user() -> User:
    return User(id=51, email="learner@example.com", hashed_password="x", is_active=True, is_superuser=False)


def test_roadmap_enrollment_forwards_authenticated_owner_and_explicit_selection(monkeypatch):
    captured = {}

    def fake_start(db, *, user, template_slug, template_version, research_project_id, acted_at=None):
        captured.update(
            {
                "db": db,
                "user_id": user.id,
                "template_slug": template_slug,
                "template_version": template_version,
                "research_project_id": research_project_id,
                "acted_at": acted_at,
            }
        )
        return {
            "action": {
                "learner_user_id": user.id,
                "template_slug": template_slug,
                "template_version": template_version,
                "research_project_id": research_project_id,
            },
            "receipt": {},
        }

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: DummyDb()
    monkeypatch.setattr(enrollment_routes, "start_recommended_practicum", fake_start)
    try:
        response = TestClient(app).post(
            "/api/v1/education/roadmap-practicum-enrollment",
            json={
                "template_slug": "research-evidence-practicum",
                "template_version": 2,
                "research_project_id": 77,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["user_id"] == 51
    assert captured["template_slug"] == "research-evidence-practicum"
    assert captured["template_version"] == 2
    assert captured["research_project_id"] == 77


def test_roadmap_enrollment_validation_requires_auth_and_returns_findings(monkeypatch):
    app.dependency_overrides[get_current_user] = _user
    monkeypatch.setattr(
        enrollment_routes,
        "validate_roadmap_enrollment_bundle",
        lambda payload: {"valid": False, "findings": ["action digest mismatch"]},
    )
    try:
        response = TestClient(app).post(
            "/api/v1/education/roadmap-practicum-enrollment/validate",
            json={"action": {}, "receipt": {}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"valid": False, "findings": ["action digest mismatch"]}


def test_roadmap_enrollment_payload_rejects_implicit_or_incomplete_selection():
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: DummyDb()
    try:
        response = TestClient(app).post(
            "/api/v1/education/roadmap-practicum-enrollment",
            json={"template_slug": "research-evidence-practicum"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_roadmap_enrollment_routes_are_registered_in_openapi():
    paths = app.openapi()["paths"]
    assert "/api/v1/education/roadmap-practicum-enrollment" in paths
    assert "/api/v1/education/roadmap-practicum-enrollment/validate" in paths
