from tests.conftest import auth_headers


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