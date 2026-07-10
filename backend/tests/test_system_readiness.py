def test_system_readiness_reports_database_and_rc3_modules(client):
    response = client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["release"] == "RC3"
    assert any(check["name"] == "database" and check["status"] == "pass" for check in payload["checks"])
    assert any(check["name"] == "rc3_modules" and check["status"] == "pass" for check in payload["checks"])
    assert "portfolio-risk-intelligence" in payload["modules"]
    assert "autonomous-portfolio-intelligence" in payload["modules"]
    assert len(payload["modules"]) == 6
    assert payload["checked_at"]
