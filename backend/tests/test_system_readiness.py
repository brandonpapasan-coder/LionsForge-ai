from app.services.market_provider_health import provider_health_registry


def test_system_readiness_reports_database_and_rc3_modules(client):
    response = client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["release"] == "RC3"
    assert any(
        check["name"] == "database" and check["status"] == "pass"
        for check in payload["checks"]
    )
    assert any(
        check["name"] == "rc3_modules" and check["status"] == "pass"
        for check in payload["checks"]
    )
    assert "portfolio-risk-intelligence" in payload["modules"]
    assert "autonomous-portfolio-intelligence" in payload["modules"]
    assert len(payload["modules"]) == 6
    assert payload["checked_at"]


def test_provider_health_report_exposes_available_and_unavailable_providers(client):
    provider_health_registry.reset()
    provider_health_registry.record_success("primary", latency_ms=12.5)
    for _ in range(provider_health_registry.failure_threshold):
        provider_health_registry.record_failure(
            "backup",
            RuntimeError("provider timeout"),
            latency_ms=250.0,
        )

    response = client.get("/api/v1/system/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checked_at"]
    providers = {item["name"]: item for item in payload["providers"]}
    assert providers["primary"]["status"] == "available"
    assert providers["primary"]["success_count"] == 1
    assert providers["primary"]["error_rate"] == 0.0
    assert providers["backup"]["status"] == "unavailable"
    assert providers["backup"]["failure_count"] == provider_health_registry.failure_threshold
    assert providers["backup"]["last_error"] == "provider timeout"

    provider_health_registry.reset()
