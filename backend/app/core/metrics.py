from app.core.observability import error_event_registry, request_metrics_registry
from app.services.market_provider_health import provider_health_registry


def render_prometheus_metrics() -> str:
    request_metrics = request_metrics_registry.snapshot()
    error_metrics = error_event_registry.snapshot()
    lines = [
        "# HELP lionsforge_http_requests_total Total HTTP requests processed.",
        "# TYPE lionsforge_http_requests_total counter",
        f"lionsforge_http_requests_total {request_metrics['request_count']}",
        "# HELP lionsforge_http_errors_total Total HTTP 5xx responses.",
        "# TYPE lionsforge_http_errors_total counter",
        f"lionsforge_http_errors_total {request_metrics['error_count']}",
        ("# HELP lionsforge_http_request_duration_ms_average Average HTTP request duration in milliseconds."),
        "# TYPE lionsforge_http_request_duration_ms_average gauge",
        (f"lionsforge_http_request_duration_ms_average {request_metrics['average_duration_ms']}"),
        ("# HELP lionsforge_application_exceptions_total Unhandled application exceptions."),
        "# TYPE lionsforge_application_exceptions_total counter",
        f"lionsforge_application_exceptions_total {error_metrics['total_count']}",
    ]

    status_codes = dict(request_metrics["status_codes"])
    lines.extend(
        [
            "# HELP lionsforge_http_responses_total HTTP responses by status code.",
            "# TYPE lionsforge_http_responses_total counter",
        ]
    )
    for status_code, count in sorted(status_codes.items()):
        lines.append(f'lionsforge_http_responses_total{{status_code="{status_code}"}} {count}')

    exception_types = dict(error_metrics["by_exception_type"])
    lines.extend(
        [
            ("# HELP lionsforge_application_exceptions_by_type_total Unhandled exceptions by type."),
            "# TYPE lionsforge_application_exceptions_by_type_total counter",
        ]
    )
    for exception_type, count in sorted(exception_types.items()):
        lines.append(f'lionsforge_application_exceptions_by_type_total{{exception_type="{exception_type}"}} {count}')

    lines.extend(
        [
            ("# HELP lionsforge_market_provider_available Market provider availability (1 available, 0 unavailable)."),
            "# TYPE lionsforge_market_provider_available gauge",
        ]
    )
    for name, health in sorted(provider_health_registry.snapshot().items()):
        available = 1 if provider_health_registry.is_available(name) else 0
        lines.append(f'lionsforge_market_provider_available{{provider="{name}"}} {available}')
        lines.append(f'lionsforge_market_provider_error_rate{{provider="{name}"}} {health.error_rate}')

    return "\n".join(lines) + "\n"
