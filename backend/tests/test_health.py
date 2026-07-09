from fastapi.testclient import TestClient

from app.main import app


def test_health_ready_and_platform_status():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/platform").status_code == 200
