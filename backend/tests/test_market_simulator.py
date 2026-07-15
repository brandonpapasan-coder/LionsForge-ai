from tests.conftest import auth_headers


def create_account(client, headers, name="Learning portfolio", starting_cash="10000.00"):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": name, "starting_cash": starting_cash},
    )
    assert response.status_code == 201
    return response.json()


def execute_trade(client, headers, account_id, symbol, side, quantity, price):
    return client.post(
        "/api/v1/market-simulator/trades",
        headers=headers,
        json={
            "account_id": account_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "execution_price": price,
        },
    )


def test_create_account_and_empty_portfolio(client):
    headers = auth_headers(client, email="simulator-account@example.com")
    account = create_account(client, headers)

    assert account["name"] == "Learning portfolio"
    assert account["starting_cash"] == "10000.00"
    assert account["cash_balance"] == "10000.00"
    assert account["status"] == "active"

    response = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["positions"] == []
    assert body["positions_value"] == "0.00"
    assert body["total_equity"] == "10000.00"
    assert body["total_return"] == "0.0000"
    assert body["concentration_risk"] == "0.0000"


def test_buy_and_sell_update_cash_position_and_performance(client):
    headers = auth_headers(client, email="simulator-trades@example.com")
    account = create_account(client, headers)

    buy = execute_trade(client, headers, account["id"], "LFTEST", "buy", "10", "100")
    assert buy.status_code == 201
    assert buy.json()["notional"] == "1000.00"

    response = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    portfolio = response.json()
    assert portfolio["account"]["cash_balance"] == "9000.00"
    assert portfolio["positions_value"] == "1000.00"
    assert portfolio["total_equity"] == "10000.00"
    assert portfolio["concentration_risk"] == "0.1000"
    assert portfolio["positions"][0]["symbol"] == "LFTEST"
    assert portfolio["positions"][0]["quantity"] == "10.000000"

    sell = execute_trade(client, headers, account["id"], "LFTEST", "sell", "4", "125")
    assert sell.status_code == 201
    assert sell.json()["notional"] == "500.00"

    response = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    portfolio = response.json()
    assert portfolio["account"]["cash_balance"] == "9500.00"
    assert portfolio["positions"][0]["quantity"] == "6.000000"
    assert portfolio["positions"][0]["last_price"] == "125.000000"
    assert portfolio["positions"][0]["unrealized_pnl"] == "150.00"
    assert portfolio["total_equity"] == "10250.00"
    assert portfolio["total_return"] == "0.0250"


def test_trade_rejects_insufficient_cash_and_position(client):
    headers = auth_headers(client, email="simulator-limits@example.com")
    account = create_account(client, headers, starting_cash="1000.00")

    response = execute_trade(client, headers, account["id"], "COSTLY", "buy", "2", "600")
    assert response.status_code == 422
    assert response.json()["detail"] == "Insufficient virtual cash"

    response = execute_trade(client, headers, account["id"], "MISSING", "sell", "1", "10")
    assert response.status_code == 422
    assert response.json()["detail"] == "Insufficient virtual position"


def test_accounts_are_owner_scoped(client):
    owner_headers = auth_headers(client, email="simulator-owner@example.com")
    other_headers = auth_headers(client, email="simulator-other@example.com")
    account = create_account(client, owner_headers)

    response = client.get(
        f"/api/v1/market-simulator/accounts/{account['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404

    response = execute_trade(client, other_headers, account["id"], "LFTEST", "buy", "1", "10")
    assert response.status_code == 404
