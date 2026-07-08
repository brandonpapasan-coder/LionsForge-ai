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
        json={"symbol": "NVDA", "quantity": "2"},
    )
    assert holding_response.status_code == 201
    assert holding_response.json()["symbol"] == "NVDA"

    value_response = client.get(f"/api/v1/portfolios/{portfolio['id']}/value", headers=headers)
    assert value_response.status_code == 200
    assert value_response.json()["total_market_value"] == "250.000000"

    list_response = client.get("/api/v1/portfolios", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert len(list_response.json()[0]["holdings"]) == 1
