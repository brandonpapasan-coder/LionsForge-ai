from tests.conftest import auth_headers


def test_event_endpoints_require_authentication(client):
    response = client.get("/api/v1/events")
    assert response.status_code in {401, 403}


def test_list_events_and_filter_by_symbol(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/events?symbol=NVDA", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert all("NVDA" in event["affected_symbols"] for event in payload["events"])


def test_get_event_detail(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/events/evt-nvda-earnings", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == "evt-nvda-earnings"
    assert payload["category"] == "earnings"
    assert payload["severity"] == "high"
    assert payload["evidence"]


def test_missing_event_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/events/missing-event", headers=headers)
    assert response.status_code == 404


def test_symbol_impact_summary_is_explainable(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/events/symbol/NVDA/impact", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["event_count"] >= 1
    assert payload["highest_severity"] in {"low", "medium", "high", "critical"}
    assert payload["impact_score"] > "0.000000"
    assert payload["follow_up_actions"]


def test_unknown_symbol_returns_monitoring_guidance(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/events/symbol/XYZ/impact", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_count"] == 0
    assert payload["highest_severity"] == "none"
    assert payload["follow_up_actions"]
