from tests.conftest import auth_headers


def create_account(client, headers, starting_cash="10000.00"):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": "Learning portfolio", "starting_cash": starting_cash},
    )
    assert response.status_code == 201
    return response.json()


def buy_position(client, headers, account_id):
    response = client.post(
        "/api/v1/market-simulator/trades",
        headers=headers,
        json={
            "account_id": account_id,
            "symbol": "LFTEST",
            "side": "buy",
            "quantity": "10",
            "execution_price": "100",
        },
    )
    assert response.status_code == 201


def session_payload(account_id):
    return {
        "account_id": account_id,
        "scenario_name": "inflation_shock",
        "steps": 30,
        "seed": 7,
        "learner_reflection": "The cash buffer reduced the simulated drawdown, while concentration increased sensitivity.",
    }


def test_market_learning_session_create_list_and_read(client):
    headers = auth_headers(client, email="market-learning@example.com")
    account = create_account(client, headers)
    buy_position(client, headers, account["id"])

    created = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=headers,
        json=session_payload(account["id"]),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["account_id"] == account["id"]
    assert body["scenario_name"] == "inflation_shock"
    assert body["risk_tier"] in {"moderate", "elevated", "high"}
    assert body["status"] == "completed"
    assert body["completed_at"]

    listed = client.get("/api/v1/market-simulator/learning-sessions", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]

    read = client.get(
        f"/api/v1/market-simulator/learning-sessions/{body['id']}",
        headers=headers,
    )
    assert read.status_code == 200
    assert read.json() == body


def test_market_learning_session_requires_meaningful_reflection(client):
    headers = auth_headers(client, email="market-learning-validation@example.com")
    account = create_account(client, headers)
    payload = session_payload(account["id"])
    payload["learner_reflection"] = "Too short"

    response = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422


def test_market_learning_sessions_are_owner_scoped(client):
    owner_headers = auth_headers(client, email="market-learning-owner@example.com")
    other_headers = auth_headers(client, email="market-learning-other@example.com")
    account = create_account(client, owner_headers)

    created = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=owner_headers,
        json=session_payload(account["id"]),
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    other_list = client.get("/api/v1/market-simulator/learning-sessions", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json() == []

    other_read = client.get(
        f"/api/v1/market-simulator/learning-sessions/{session_id}",
        headers=other_headers,
    )
    assert other_read.status_code == 404


def test_learning_session_creation_does_not_mutate_portfolio(client):
    headers = auth_headers(client, email="market-learning-immutable@example.com")
    account = create_account(client, headers)
    buy_position(client, headers, account["id"])

    response = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=headers,
        json=session_payload(account["id"]),
    )
    assert response.status_code == 201

    portfolio = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    assert portfolio.status_code == 200
    assert portfolio.json()["positions"][0]["last_price"] == "100.000000"
    assert portfolio.json()["total_equity"] == "10000.00"
