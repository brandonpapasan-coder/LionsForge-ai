from tests.conftest import auth_headers


def _create_portfolio(client, headers, name="Risk Portfolio"):
    response = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": name, "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()


def _add_holding(client, headers, portfolio_id, symbol, quantity, average_cost="100"):
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers=headers,
        json={"symbol": symbol, "quantity": quantity, "average_cost": average_cost},
    )
    assert response.status_code == 201
    return response.json()


def test_empty_portfolio_returns_explainable_high_risk_report(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers, name="Empty")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/risk", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == portfolio["id"]
    assert payload["portfolio_risk_score"] == "100.000000"
    assert payload["portfolio_health_score"] == "0.000000"
    assert payload["position_count"] == 0
    assert payload["sector_exposure"] == []
    assert payload["recommendations"][0]["category"] == "portfolio_empty"


def test_single_position_portfolio_flags_concentration_risk(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers, name="Concentrated")
    _add_holding(client, headers, portfolio["id"], "NVDA", "4", "100")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/health", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["largest_position_symbol"] == "NVDA"
    assert payload["largest_position_percent"] == "100.000000"
    assert payload["top_position_risks"][0]["risk_level"] == "high"
    assert any(item["category"] == "concentration" for item in payload["recommendations"])
    assert any(item["category"] == "diversification" for item in payload["recommendations"])


def test_diversified_portfolio_returns_sector_allocation_contract(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers, name="Diversified")
    _add_holding(client, headers, portfolio["id"], "AAPL", "1", "200")
    _add_holding(client, headers, portfolio["id"], "JPM", "2", "100")
    _add_holding(client, headers, portfolio["id"], "JNJ", "2", "100")
    _add_holding(client, headers, portfolio["id"], "XOM", "2", "100")
    _add_holding(client, headers, portfolio["id"], "PG", "2", "100")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/allocation", headers=headers)

    assert response.status_code == 200
    allocation = response.json()
    sectors = {item["sector"] for item in allocation}
    assert "Technology" in sectors
    assert "Financials" in sectors
    assert "Healthcare" in sectors
    assert all("market_value" in item and "allocation_percent" in item for item in allocation)

    risk_response = client.get(f"/api/v1/portfolios/{portfolio['id']}/risk", headers=headers)
    assert risk_response.status_code == 200
    risk_payload = risk_response.json()
    assert risk_payload["position_count"] == 5
    assert risk_payload["diversification_score"] >= "50.000000"


def test_cash_allocation_recommendation_is_triggered(client):
    headers = auth_headers(client)
    portfolio = _create_portfolio(client, headers, name="Cash Heavy")
    _add_holding(client, headers, portfolio["id"], "AAPL", "1", "200")

    deposit = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/transactions",
        headers=headers,
        json={"transaction_type": "deposit", "cash_amount": "1000"},
    )
    assert deposit.status_code == 201

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/risk", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["cash_allocation_percent"] >= "40.000000"
    assert any(item["category"] == "cash_allocation" for item in payload["recommendations"])


def test_portfolio_risk_endpoint_requires_authentication(client):
    response = client.get("/api/v1/portfolios/1/risk")
    assert response.status_code in {401, 403}


def test_portfolio_risk_endpoint_returns_404_for_other_user(client):
    owner_headers = auth_headers(client, email="owner@example.com")
    other_headers = auth_headers(client, email="other@example.com")
    portfolio = _create_portfolio(client, owner_headers, name="Private")

    response = client.get(f"/api/v1/portfolios/{portfolio['id']}/risk", headers=other_headers)

    assert response.status_code == 404
