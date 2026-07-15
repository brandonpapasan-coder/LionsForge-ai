from app.core.observability import error_event_registry, request_metrics_registry
from tests.conftest import auth_headers


def reset_metrics() -> None:
    request_metrics_registry.reset()
    error_event_registry.reset()


def test_request_id_header_is_preserved(client):
    reset_metrics()
    request_id = "11111111-1111-1111-1111-111111111111"

    response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    snapshot = request_metrics_registry.snapshot()
    assert snapshot["request_count"] == 1
    assert snapshot["status_codes"] == {200: 1}


def test_invalid_request_id_is_replaced(client):
    reset_metrics()

    response = client.get("/health", headers={"X-Request-ID": "not-a-uuid"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "not-a-uuid"
    assert len(response.headers["x-request-id"]) == 36


def test_operational_metrics_require_authentication(client):
    reset_metrics()

    response = client.get("/api/v1/system/metrics")

    assert response.status_code == 401


def test_operational_metrics_report_request_and_exception_counts(client):
    reset_metrics()
    headers = auth_headers(client)
    error_event_registry.record(
        request_id="22222222-2222-2222-2222-222222222222",
        method="POST",
        path="/api/v1/test",
        exception=ValueError("invalid"),
    )

    response = client.get("/api/v1/system/metrics", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    # The endpoint snapshots metrics before middleware records the metrics request itself.
    assert payload["request_count"] >= 2
    assert payload["application_exception_count"] == 1
    assert payload["exceptions_by_type"] == {"ValueError": 1}
    assert payload["last_exception"]["request_id"] == "22222222-2222-2222-2222-222222222222"
    assert payload["last_exception"]["exception_type"] == "ValueError"
