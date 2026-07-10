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
