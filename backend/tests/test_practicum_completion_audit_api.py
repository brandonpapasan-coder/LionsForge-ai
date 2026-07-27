from types import SimpleNamespace

import pytest
from fastapi import status

from app.api.deps import get_current_user
from app.api.routes import practicum_completion_audit
from app.db.session import get_db
from app.main import app

BASE = "/api/v1/education/practica"


@pytest.fixture(autouse=True)
def completion_audit_dependencies():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, is_superuser=False)
    app.dependency_overrides[get_db] = lambda: object()
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_completion_audit_export_uses_authenticated_user(client, monkeypatch):
    captured: dict = {}

    def fake_export(db, *, enrollment_id, user):
        captured.update(enrollment_id=enrollment_id, user_id=user.id)
        return {
            "record": {"schema": "lionsforge.practicum-completion-record"},
            "receipt": {"record_sha256": "a" * 64},
        }

    monkeypatch.setattr(practicum_completion_audit, "export_completion_bundle", fake_export)

    response = client.get(f"{BASE}/enrollments/42/completion-audit")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["receipt"]["record_sha256"] == "a" * 64
    assert captured == {"enrollment_id": 42, "user_id": 7}


def test_completion_audit_validation_requires_authentication_and_returns_findings(client, monkeypatch):
    monkeypatch.setattr(
        practicum_completion_audit,
        "validate_completion_bundle",
        lambda payload: {"valid": False, "findings": ["record digest mismatch"]},
    )

    response = client.post(
        f"{BASE}/completion-audit/validate",
        json={"record": {}, "receipt": {}},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"valid": False, "findings": ["record digest mismatch"]}


def test_completion_audit_route_is_present_in_openapi(client):
    schema = client.get("/openapi.json").json()

    assert f"{BASE}/enrollments/{{enrollment_id}}/completion-audit" in schema["paths"]
    assert f"{BASE}/completion-audit/validate" in schema["paths"]
