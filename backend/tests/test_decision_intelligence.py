from tests.conftest import auth_headers


def test_decision_endpoint_requires_authentication(client):
    response = client.get("/api/v1/decisions/NVDA")
    assert response.status_code in {401, 403}


def test_decision_endpoint_returns_unified_explainable_recommendation(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/decisions/NVDA", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["action"] in {"investigate", "monitor", "review_risk", "defer"}
    assert payload["priority"] in {"low", "medium", "high"}
    assert payload["opportunity_score"] >= "0.000000"
    assert payload["risk_score"] >= "0.000000"
    assert payload["confidence_score"] >= "0.000000"
    assert {driver["source"] for driver in payload["drivers"]} == {"factor", "research", "event", "risk"}
    assert payload["rationale"]
    assert payload["next_actions"]
    assert payload["limitations"]


def test_decision_endpoint_normalizes_symbol(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/decisions/aapl", headers=headers)

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"


def test_unknown_symbol_returns_deferred_or_monitorable_decision(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/decisions/XYZ", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "XYZ"
    assert payload["action"] in {"defer", "monitor", "review_risk", "investigate"}
    assert any("mock" in item.lower() or "fallback" in item.lower() for item in payload["limitations"])
