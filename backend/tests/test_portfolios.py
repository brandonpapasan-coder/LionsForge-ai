from tests.conftest import auth_headers


def test_create_portfolio_and_add_holding(client):
    headers = auth_headers(client)
    portfolio_response = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": "Long Term", "base_currency": "USD"},
    )
    assert portfolio_response.status_code == 201
    portfolio = portfolio_response.json()
    assert portfolio["name"] == "Long Term"

    holding_response = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/holdings",
        headers=headers,
        json={"symbol": "NVDA", "quantity": "2", "average_cost": "100"},
    )
    assert holding_response.status_code == 201
    assert holding_response.json()["symbol"] == "NVDA"

    value_response = client.get(f"/api/v1/portfolios/{portfolio['id']}/value", headers=headers)
    assert value_response.status_code == 200
    assert value_response.json()["total_market_value"] == "250.000000"

    performance_response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/performance",
        headers=headers,
    )
    assert performance_response.status_code == 200
    performance = performance_response.json()
    assert performance["total_cost_basis"] == "200.000000"
    assert performance["total_unrealized_gain_loss"] == "50.000000"

    holdings_value_response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/holdings/value",
        headers=headers,
    )
    assert holdings_value_response.status_code == 200
    holding_value = holdings_value_response.json()[0]
    assert holding_value["symbol"] == "NVDA"
    assert holding_value["market_value"] == "250.000000"

    allocation_response = client.get(
        f"/api/v1/portfolios/{portfolio['id']}/holdings/allocation",
        headers=headers,
    )
    assert allocation_response.status_code == 200
    allocation = allocation_response.json()[0]
    assert allocation["symbol"] == "NVDA"
    assert allocation["allocation_percent"] == "100.000000"

    list_response = client.get("/api/v1/portfolios", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert len(list_response.json()[0]["holdings"]) == 1
