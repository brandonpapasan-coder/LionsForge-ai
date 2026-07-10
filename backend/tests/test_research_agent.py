from tests.conftest import auth_headers


def test_research_agent_requires_authentication(client):
    response = client.get("/api/v1/research-agent/NVDA")
    assert response.status_code in {401, 403}


def test_research_agent_returns_explainable_report(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research-agent/NVDA", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["business_summary"]
    assert payload["market_context"]
    assert payload["factor_score"] >= "0.000000"
    assert payload["factor_rating"] in {"avoid", "watch", "neutral", "outperform"}
    assert payload["confidence_score"] >= "0.000000"
    assert payload["findings"]
    assert {item["category"] for item in payload["findings"]} == {"strength", "risk", "opportunity", "question"}
    assert payload["bull_case"]
    assert payload["bear_case"]
    assert payload["open_questions"]
    assert payload["limitations"]


def test_research_agent_handles_unknown_symbol(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research-agent/XYZ", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "XYZ"
    assert "validated company profile" in payload["business_summary"]
    assert payload["freshness"] in {"mock", "fresh", "stale"}
