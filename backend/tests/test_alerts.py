from tests.conftest import auth_headers


def test_create_list_and_evaluate_alerts(client):
    headers = auth_headers(client)
    create_response = client.post(
        "/api/v1/alerts",
        headers=headers,
        json={"symbol": "AAPL", "condition": "above", "target_price": "200", "note": "Watch breakout"},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["is_active"] is True

    list_response = client.get("/api/v1/alerts", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    evaluate_response = client.get("/api/v1/alerts/evaluate", headers=headers)
    assert evaluate_response.status_code == 200
    evaluation = evaluate_response.json()[0]
    assert evaluation["symbol"] == "AAPL"
    assert evaluation["triggered"] is True
