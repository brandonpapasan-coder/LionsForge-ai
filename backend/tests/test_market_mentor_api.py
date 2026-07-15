from tests.conftest import auth_headers


def create_account(client, headers, starting_cash="10000.00"):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": "Mentor portfolio", "starting_cash": starting_cash},
    )
    assert response.status_code == 201
    return response.json()


def buy_position(client, headers, account_id, symbol="LFTEST", quantity="10", price="100"):
    response = client.post(
        "/api/v1/market-simulator/trades",
        headers=headers,
        json={
            "account_id": account_id,
            "symbol": symbol,
            "side": "buy",
            "quantity": quantity,
            "execution_price": price,
        },
    )
    assert response.status_code == 201


def feedback_payload():
    return {"scenario_name": "inflation_shock", "steps": 30, "seed": 7}


def test_market_mentor_feedback_is_authenticated_and_deterministic(client):
    headers = auth_headers(client, email="mentor-feedback@example.com")
    account = create_account(client, headers)
    buy_position(client, headers, account["id"])

    url = f"/api/v1/market-simulator/portfolio/{account['id']}/mentor-feedback"
    first = client.post(url, headers=headers, json=feedback_payload())
    second = client.post(url, headers=headers, json=feedback_payload())

    assert first.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["stress"]["account_id"] == account["id"]
    assert body["feedback"]["risk_tier"] in {"moderate", "elevated", "high"}
    assert len(body["feedback"]["observations"]) == 3
    assert len(body["feedback"]["reflection_questions"]) == 3
    assert "not financial advice" in body["feedback"]["disclaimer"].lower()


def test_market_mentor_feedback_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="mentor-owner@example.com")
    other_headers = auth_headers(client, email="mentor-other@example.com")
    account = create_account(client, owner_headers)

    response = client.post(
        f"/api/v1/market-simulator/portfolio/{account['id']}/mentor-feedback",
        headers=other_headers,
        json=feedback_payload(),
    )
    assert response.status_code == 404


def test_market_mentor_feedback_does_not_mutate_portfolio(client):
    headers = auth_headers(client, email="mentor-immutable@example.com")
    account = create_account(client, headers)
    buy_position(client, headers, account["id"], quantity="5", price="200")

    response = client.post(
        f"/api/v1/market-simulator/portfolio/{account['id']}/mentor-feedback",
        headers=headers,
        json=feedback_payload(),
    )
    assert response.status_code == 200

    portfolio = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    assert portfolio.status_code == 200
    assert portfolio.json()["positions"][0]["last_price"] == "200.000000"
    assert portfolio.json()["total_equity"] == "10000.00"
