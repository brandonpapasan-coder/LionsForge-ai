from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


class BrokenDatabaseSession:
    def execute(self, _statement):
        raise RuntimeError("database unavailable")


def test_health_ready_and_platform_status():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        readiness = client.get("/ready")
        assert readiness.status_code == 200
        assert readiness.json() == {"status": "ready", "database": "available"}
        assert client.get("/").status_code == 200
        assert client.get("/platform").status_code == 200


def test_ready_returns_503_when_database_is_unavailable():
    def override_get_db():
        yield BrokenDatabaseSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Database dependency is unavailable."}


def test_request_id_is_preserved_when_valid_uuid_is_supplied():
    request_id = str(uuid4())

    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": request_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id


def test_request_id_is_generated_for_missing_or_invalid_header():
    with TestClient(app) as client:
        missing_header_response = client.get("/health")
        invalid_header_response = client.get(
            "/health",
            headers={"x-request-id": "not-a-uuid"},
        )

    generated_id = missing_header_response.headers["x-request-id"]
    replacement_id = invalid_header_response.headers["x-request-id"]
    assert str(UUID(generated_id)) == generated_id
    assert str(UUID(replacement_id)) == replacement_id
    assert replacement_id != "not-a-uuid"
