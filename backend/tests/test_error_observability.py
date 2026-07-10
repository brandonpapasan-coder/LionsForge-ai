from app.core.metrics import render_prometheus_metrics
from app.core.observability import error_event_registry


def test_error_event_registry_tracks_exception_summary():
    error_event_registry.reset()

    error_event_registry.record(
        request_id="11111111-1111-1111-1111-111111111111",
        method="GET",
        path="/api/v1/test",
        exception=RuntimeError("boom"),
    )

    snapshot = error_event_registry.snapshot()
    assert snapshot["total_count"] == 1
    assert snapshot["by_exception_type"] == {"RuntimeError": 1}
    last_event = snapshot["last_event"]
    assert last_event is not None
    assert last_event.request_id == "11111111-1111-1111-1111-111111111111"
    assert last_event.method == "GET"
    assert last_event.path == "/api/v1/test"
    assert last_event.exception_type == "RuntimeError"
    assert last_event.occurred_at is not None

    error_event_registry.reset()


def test_prometheus_metrics_include_application_exception_counts():
    error_event_registry.reset()
    error_event_registry.record(
        request_id="22222222-2222-2222-2222-222222222222",
        method="POST",
        path="/api/v1/test",
        exception=ValueError("invalid"),
    )

    metrics = render_prometheus_metrics()

    assert "lionsforge_application_exceptions_total 1" in metrics
    assert (
        'lionsforge_application_exceptions_by_type_total{exception_type="ValueError"} 1'
        in metrics
    )

    error_event_registry.reset()
