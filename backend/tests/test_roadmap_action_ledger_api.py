from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User


class FakeDB:
    pass


def test_roadmap_action_ledger_routes_forward_authenticated_owner(monkeypatch):
    user = User(id=42, email="learner@example.com", hashed_password="x", is_active=True)
    fake_db = FakeDB()
    captured: dict[str, object] = {}

    def fake_export(db, *, user, **filters):
        captured.update({"db": db, "user": user, **filters})
        return {"ledger": {"learner_user_id": user.id}, "receipt": {"ledger_sha256": "a" * 64}}

    monkeypatch.setattr("app.api.routes.roadmap_action_ledger.export_roadmap_action_ledger", fake_export)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: fake_db
    try:
        response = TestClient(app).get(
            "/api/v1/education/roadmap-action-ledger",
            params={"template_slug": "source-triangulation", "reason_code": "adds_not_yet_demonstrated_competency"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["db"] is fake_db
    assert captured["user"] is user
    assert captured["template_slug"] == "source-triangulation"
    assert captured["reason_code"] == "adds_not_yet_demonstrated_competency"


def test_roadmap_action_ledger_validation_route(monkeypatch):
    user = User(id=42, email="learner@example.com", hashed_password="x", is_active=True)
    monkeypatch.setattr(
        "app.api.routes.roadmap_action_ledger.validate_roadmap_action_ledger_bundle",
        lambda payload: {"valid": False, "findings": ["ledger digest mismatch"]},
    )
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = TestClient(app).post(
            "/api/v1/education/roadmap-action-ledger/validate",
            json={"ledger": {}, "receipt": {}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"valid": False, "findings": ["ledger digest mismatch"]}


def test_roadmap_action_record_persistence_and_migration_are_registered():
    root = Path(__file__).resolve().parents[1]
    model = (root / "app/models/roadmap_action_record.py").read_text()
    migration = (root / "alembic/versions/0036_roadmap_action_ledger.py").read_text()
    flow = (root / "app/services/roadmap_practicum_enrollment_flow.py").read_text()
    main = (root / "app/main.py").read_text()

    assert 'UniqueConstraint("enrollment_id", name="uq_roadmap_action_record_enrollment")' in model
    assert 'down_revision: str | None = "0035_research_practicum"' in migration
    assert "RoadmapActionRecord(" in flow
    assert "action_receipt_sha256=sha256_digest(receipt)" in flow
    assert "db.commit()" in flow
    assert "roadmap_action_ledger_router" in main
