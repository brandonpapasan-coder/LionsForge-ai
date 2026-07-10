from app.core.observability import request_metrics_registry
from app.services.market_provider_health import provider_health_registry


def render_prometheus_metrics() -> str:
    request_metrics = request_metrics_registry.snapshot()
    lines = [
        "# HELP lionsforge_http_requests_total Total HTTP requests processed.",
        "# TYPE lionsforge_http_requests_total counter",
        f"lionsforge_http_requests_total {request_metrics['request_count']}",
        "# HELP lionsforge_http_errors_total Total HTTP 5xx responses.",
        "# TYPE lionsforge_http_errors_total counter",
        f"lionsforge_http_errors_total {request_metrics['error_count']}",
        "# HELP lionsforge_http_request_duration_ms_average Average HTTP request duration in milliseconds.",
        "# TYPE lionsforge_http_request_duration_ms_average gauge",
        (
            "lionsforge_http_request_duration_ms_average "
            f"{request_metrics['average_duration_ms']}"
        ),
    ]

    status_codes = dict(request_metrics["status_codes"])
    lines.extend(
        [
            "# HELP lionsforge_http_responses_total HTTP responses by status code.",
            "# TYPE lionsforge_http_responses_total counter",
        ]
    )
    for status_code, count in sorted(status_codes.items()):
        lines.append(
            'lionsforge_http_responses_total{status_code="'
            f"{status_code}"
            f'"}} {count}'
        )

    lines.extend(
        [
            "# HELP lionsforge_market_provider_available Market provider availability (1 available, 0 unavailable).",
            "# TYPE lionsforge_market_provider_available gauge",
        ]
    )
    for name, health in sorted(provider_health_registry.snapshot().items()):
        available = 1 if provider_health_registry.is_available(name) else 0
        lines.append(
            'lionsforge_market_provider_available{provider="'
            f"{name}"
            f'"}} {available}'
        )
        lines.append(
            'lionsforge_market_provider_error_rate{provider="'
            f"{name}"
            f'"}} {health.error_rate}'
        )

    return "\n".join(lines) + "\n"
