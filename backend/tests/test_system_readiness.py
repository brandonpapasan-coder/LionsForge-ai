from tests.conftest import auth_headers


ACTIVE_MODULES = {
    "research-orchestration",
    "evidence-validation",
    "knowledge-graph",
    "knowledge-memory",
    "education",
    "mentor",
    "missions",
    "multi-agent-consensus",
}

DISCONTINUED_FINANCE_MODULES = {
    "portfolio-risk-intelligence",
    "factor-intelligence",
    "event-intelligence",
    "decision-intelligence",
    "autonomous-portfolio-intelligence",
}


def test_system_readiness_reports_database_and_active_modules(client):
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
        check["name"] == "active_modules" and check["status"] == "pass"
        for check in payload["checks"]
    )
    assert set(payload["modules"]) == ACTIVE_MODULES
    assert DISCONTINUED_FINANCE_MODULES.isdisjoint(payload["modules"])
    assert payload["checked_at"]


def test_provider_health_requires_authentication(client):
    response = client.get("/api/v1/system/providers")

    assert response.status_code == 401


def test_provider_health_reports_openai_without_model_request(client):
    response = client.get("/api/v1/system/providers", headers=auth_headers(client))

    assert response.status_code == 200
    payload = response.json()
    provider = payload["providers"]["openai_mentor"]
    assert provider["provider"] == "openai"
    assert provider["enabled"] is False
    assert provider["status"] == "disabled"
    assert provider["model"]
    assert provider["timeout_seconds"] > 0
    assert provider["max_retries"] >= 0
    assert payload["checked_at"]
