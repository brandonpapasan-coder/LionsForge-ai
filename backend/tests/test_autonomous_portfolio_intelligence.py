from tests.conftest import auth_headers


def _create_portfolio(client, headers, name="Autonomous Portfolio"):
    response = client.post("/api/v1/portfolios", headers=headers, json={"name": name, "base_currency": "USD"})
    assert response.status_code == 201
    return response.json()


def _add_holding(client, headers, portfolio_id, symbol, quantity):
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers=headers,
        json={"symbol": symbol, "quantity": quantity, "average_cost": "100"},
    )
    assert response.status_code == 201


def test_autonomous_portfolio_intelligence_requires_authentication(client):
    response = client.get("/api/v1/portfolios/1/intelligence")
    assert response.status_code in {401, 403}


def test_autonomous_portfolio_intelligence_ranks_holdings_and_builds_heatmap(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers)
    _add_holding(client, headers, portfolio["id"], "NVDA", "2")
    _add_holding(client, headers, portfolio["id"], "MSFT", "2")
    _add_holding(client, headers, portfolio["id"], "AAPL", "1")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/intelligence", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == portfolio["id"]
    assert len(payload["holdings_ranked"]) == 3
    assert len(payload["risk_heatmap"]) == 3
    opportunities = [item["opportunity_score"] for item in payload["holdings_ranked"]]
    assert opportunities == sorted(opportunities, reverse=True)
    weighted_risks = [item["weighted_risk_score"] for item in payload["risk_heatmap"]]
    assert weighted_risks == sorted(weighted_risks, reverse=True)
    assert payload["recommendations"]


def test_empty_portfolio_returns_explainable_report(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers, name="Empty")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/intelligence", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["holdings_ranked"] == []
    assert payload["risk_heatmap"] == []
    assert payload["aggregate_opportunity_score"] == "0.000000"
    assert payload["recommendations"]


def test_autonomous_portfolio_intelligence_enforces_ownership(client):
    owner_headers = auth_headers(client, email="portfolio-owner@example.com")
    other_headers = auth_headers(client, email="portfolio-other@example.com")
    portfolio = _create_portfolio(client, owner_headers)

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/intelligence", headers=other_headers)
    assert response.status_code == 404
