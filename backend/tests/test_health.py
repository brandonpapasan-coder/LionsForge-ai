from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.observability import request_metrics_registry
from app.db.session import get_db
from app.main import app
from app.services.market_provider_health import provider_health_registry


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


def test_prometheus_metrics_endpoint_exposes_request_and_provider_metrics():
    request_metrics_registry.reset()
    provider_health_registry.reset()
    provider_health_registry.record_success("primary", latency_ms=10.0)
    for _ in range(provider_health_registry.failure_threshold):
        provider_health_registry.record_failure(
            "backup",
            RuntimeError("timeout"),
            latency_ms=250.0,
        )

    request_metrics_registry.record(status_code=200, duration_ms=20.0)
    request_metrics_registry.record(status_code=503, duration_ms=40.0)

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "lionsforge_http_requests_total 2" in body
    assert "lionsforge_http_errors_total 1" in body
    assert 'lionsforge_http_responses_total{status_code="200"} 1' in body
    assert 'lionsforge_http_responses_total{status_code="503"} 1' in body
    assert 'lionsforge_market_provider_available{provider="primary"} 1' in body
    assert 'lionsforge_market_provider_available{provider="backup"} 0' in body

    request_metrics_registry.reset()
    provider_health_registry.reset()
