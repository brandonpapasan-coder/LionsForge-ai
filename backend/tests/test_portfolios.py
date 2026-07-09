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


def test_portfolio_transactions_update_holdings_and_cash(client):
    headers = auth_headers(client)
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": "Trading", "base_currency": "USD"},
    ).json()

    deposit = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/transactions",
        headers=headers,
        json={"transaction_type": "deposit", "cash_amount": "1000"},
    )
    assert deposit.status_code == 201

    buy = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/transactions",
        headers=headers,
        json={"transaction_type": "buy", "symbol": "AAPL", "quantity": "2", "price": "100"},
    )
    assert buy.status_code == 201

    analytics = client.get(f"/api/v1/portfolios/{portfolio['id']}/analytics", headers=headers)
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["cash_balance"] == "800.000000"
    assert payload["holdings"][0]["symbol"] == "AAPL"
    assert payload["holdings"][0]["quantity"] == "2.000000"
    assert payload["total_cost_basis"] == "200.000000"

    sell = client.post(
        f"/api/v1/portfolios/{portfolio['id']}/transactions",
        headers=headers,
        json={"transaction_type": "sell", "symbol": "AAPL", "quantity": "1", "price": "125"},
    )
    assert sell.status_code == 201

    transactions = client.get(f"/api/v1/portfolios/{portfolio['id']}/transactions", headers=headers)
    assert transactions.status_code == 200
    assert len(transactions.json()) == 3

    analytics_after_sell = client.get(f"/api/v1/portfolios/{portfolio['id']}/analytics", headers=headers).json()
    assert analytics_after_sell["cash_balance"] == "925.000000"
    assert analytics_after_sell["holdings"][0]["quantity"] == "1.000000"


def test_portfolio_insights_and_watchlist_sync(client):
    headers = auth_headers(client)
    portfolio = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": "Research Linked", "base_currency": "USD"},
    ).json()
    client.post(
        f"/api/v1/portfolios/{portfolio['id']}/transactions",
        headers=headers,
        json={"transaction_type": "buy", "symbol": "NVDA", "quantity": "2", "price": "100"},
    )
    client.post(
        "/api/v1/research/reports",
        json={"symbol": "NVDA", "persist": True},
        headers=headers,
    )

    insights = client.get(f"/api/v1/portfolios/{portfolio['id']}/insights", headers=headers)
    assert insights.status_code == 200
    insight_payload = insights.json()
    assert insight_payload["research_coverage_percent"] == "100.000000"
    assert insight_payload["insights"]
    assert any("NVDA" in insight["supporting_symbols"] for insight in insight_payload["insights"])

    sync = client.post(f"/api/v1/portfolios/{portfolio['id']}/watchlist-sync", headers=headers)
    assert sync.status_code == 200
    assert sync.json()["added_symbols"] == ["NVDA"]
    assert sync.json()["tickers"] == ["NVDA"]
