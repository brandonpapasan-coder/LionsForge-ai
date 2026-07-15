from tests.conftest import auth_headers


def test_advanced_alert_requires_authentication(client):
    response = client.post(
        "/api/v1/advanced-alerts/events",
        json={"category": "earnings", "headline": "Quarterly results", "detail": "Results released."},
    )
    assert response.status_code == 401


def test_create_earnings_alert_persists_notification(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/advanced-alerts/events",
        headers=headers,
        json={
            "category": "earnings",
            "headline": "Revenue exceeds expectations",
            "detail": "Quarterly revenue was above the supplied estimate.",
            "symbol": "msft",
            "severity": "warning",
            "source_label": "earnings release",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["category"] == "earnings"
    assert payload["symbol"] == "MSFT"
    assert payload["notification_id"]
    assert payload["event_id"]

    notifications = client.get("/api/v1/alerts/notifications", headers=headers)
    assert notifications.status_code == 200
    assert any(item["id"] == payload["notification_id"] for item in notifications.json())


def test_supported_event_categories_are_delivered(client):
    headers = auth_headers(client)
    categories = ["sec_filing", "analyst_change", "macro_event"]
    for category in categories:
        response = client.post(
            "/api/v1/advanced-alerts/events",
            headers=headers,
            json={
                "category": category,
                "headline": f"{category} update",
                "detail": "Deterministic event detail for validation.",
                "symbol": "aapl" if category != "macro_event" else None,
            },
        )
        assert response.status_code == 201
        assert response.json()["category"] == category


def test_portfolio_risk_alert_requires_threshold_context(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/advanced-alerts/events",
        headers=headers,
        json={
            "category": "portfolio_risk",
            "headline": "Risk threshold exceeded",
            "detail": "Concentration risk increased.",
        },
    )
    assert response.status_code == 422


def test_portfolio_risk_alert_rejects_score_below_threshold(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/advanced-alerts/events",
        headers=headers,
        json={
            "category": "portfolio_risk",
            "headline": "Risk threshold review",
            "detail": "Risk remains below the configured threshold.",
            "portfolio_id": 1,
            "risk_score": 54,
            "threshold": 60,
        },
    )
    assert response.status_code == 422


def test_portfolio_risk_alert_includes_explainable_threshold(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/advanced-alerts/events",
        headers=headers,
        json={
            "category": "portfolio_risk",
            "headline": "Concentration threshold exceeded",
            "detail": "Largest position concentration increased.",
            "portfolio_id": 1,
            "risk_score": 72,
            "threshold": 65,
            "severity": "critical",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["severity"] == "critical"
    assert "risk score 72 met threshold 65" in payload["message"]
