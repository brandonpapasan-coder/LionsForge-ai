from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.api.routes import learner_competency_portfolio as portfolio_routes


class DummyDb:
    pass


def _user() -> User:
    return User(id=41, email="learner@example.com", hashed_password="x", is_active=True, is_superuser=False)


def test_portfolio_route_forwards_authenticated_owner_and_filters(monkeypatch):
    captured = {}

    def fake_export(db, *, user, competency_key=None, template_slug=None, generated_at=None):
        captured.update(
            {
                "db": db,
                "user_id": user.id,
                "competency_key": competency_key,
                "template_slug": template_slug,
                "generated_at": generated_at,
            }
        )
        return {"portfolio": {"learner_user_id": user.id}, "receipt": {}, "exclusions": []}

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: DummyDb()
    monkeypatch.setattr(portfolio_routes, "export_competency_portfolio", fake_export)
    try:
        response = TestClient(app).get(
            "/api/v1/education/competency-portfolio?competency_key=evidence_validation&template_slug=research-foundations"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["portfolio"]["learner_user_id"] == 41
    assert captured["user_id"] == 41
    assert captured["competency_key"] == "evidence_validation"
    assert captured["template_slug"] == "research-foundations"


def test_portfolio_validation_route_requires_auth_and_returns_findings(monkeypatch):
    app.dependency_overrides[get_current_user] = _user
    monkeypatch.setattr(
        portfolio_routes,
        "validate_competency_portfolio_bundle",
        lambda payload: {"valid": False, "findings": ["portfolio digest mismatch"]},
    )
    try:
        response = TestClient(app).post(
            "/api/v1/education/competency-portfolio/validate",
            json={"portfolio": {}, "receipt": {}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"valid": False, "findings": ["portfolio digest mismatch"]}


def test_portfolio_routes_are_registered_in_openapi():
    paths = app.openapi()["paths"]
    assert "/api/v1/education/competency-portfolio" in paths
    assert "/api/v1/education/competency-portfolio/validate" in paths
