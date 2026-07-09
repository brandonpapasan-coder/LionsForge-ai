from tests.conftest import auth_headers


def test_alert_evaluation_creates_notification_and_mark_read(client):
    headers = auth_headers(client)
    alert_response = client.post(
        "/api/v1/alerts",
        headers=headers,
        json={"symbol": "AAPL", "condition": "above", "target_price": "200", "note": "Watch breakout"},
    )
    assert alert_response.status_code == 201

    evaluate_response = client.get("/api/v1/alerts/evaluate", headers=headers)
    assert evaluate_response.status_code == 200
    evaluation = evaluate_response.json()[0]
    assert evaluation["triggered"] is True
    assert evaluation["notification_id"] is not None

    notifications_response = client.get("/api/v1/alerts/notifications", headers=headers)
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["symbol"] == "AAPL"
    assert notifications[0]["notification_type"] == "price_alert"
    assert notifications[0]["severity"] == "warning"
    assert notifications[0]["is_read"] is False

    mark_read_response = client.post(
        f"/api/v1/alerts/notifications/{notifications[0]['id']}/read",
        headers=headers,
    )
    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["is_read"] is True
    assert mark_read_response.json()["read_at"] is not None

    unread_response = client.get("/api/v1/alerts/notifications?unread_only=true", headers=headers)
    assert unread_response.status_code == 200
    assert unread_response.json() == []


def test_alert_automation_rule_run_delivers_notification(client):
    headers = auth_headers(client)
    create_response = client.post(
        "/api/v1/alerts/automation-rules",
        headers=headers,
        json={
            "name": "Daily AAPL summary",
            "rule_type": "daily_market_summary",
            "schedule": "daily",
            "symbol": "AAPL",
        },
    )
    assert create_response.status_code == 201
    rule = create_response.json()
    assert rule["name"] == "Daily AAPL summary"
    assert rule["is_active"] is True

    list_response = client.get("/api/v1/alerts/automation-rules", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    run_response = client.post(f"/api/v1/alerts/automation-rules/{rule['id']}/run", headers=headers)
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["rule_id"] == rule["id"]
    assert run_payload["notification_id"] is not None
    assert run_payload["delivery_status"] == "delivered"

    notifications_response = client.get("/api/v1/alerts/notifications", headers=headers)
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "daily_market_summary"
    assert notifications[0]["symbol"] == "AAPL"
