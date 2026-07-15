from tests.conftest import auth_headers


def create_account(client, headers, starting_cash="10000.00"):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": "Scenario portfolio", "starting_cash": starting_cash},
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
    return response.json()


def scenario_payload(**overrides):
    payload = {
        "scenario_name": "bear_market",
        "initial_price": "100.00",
        "steps": 20,
        "seed": 42,
    }
    payload.update(overrides)
    return payload


def test_authenticated_scenario_replay_is_deterministic(client):
    headers = auth_headers(client, email="scenario-replay@example.com")

    first = client.post(
        "/api/v1/market-simulator/scenarios/run",
        headers=headers,
        json=scenario_payload(),
    )
    second = client.post(
        "/api/v1/market-simulator/scenarios/run",
        headers=headers,
        json=scenario_payload(),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["scenario_name"] == "bear_market"
    assert first.json()["steps"] == 20
    assert len(first.json()["points"]) == 20


def test_scenario_endpoint_requires_authentication(client):
    response = client.post(
        "/api/v1/market-simulator/scenarios/run",
        json=scenario_payload(),
    )
    assert response.status_code in {401, 403}


def test_scenario_endpoint_validates_catalog_and_bounds(client):
    headers = auth_headers(client, email="scenario-validation@example.com")

    response = client.post(
        "/api/v1/market-simulator/scenarios/run",
        headers=headers,
        json=scenario_payload(scenario_name="unknown"),
    )
    assert response.status_code == 422

    response = client.post(
        "/api/v1/market-simulator/scenarios/run",
        headers=headers,
        json=scenario_payload(steps=5001),
    )
    assert response.status_code == 422


def test_portfolio_stress_applies_scenario_without_mutating_positions(client):
    headers = auth_headers(client, email="scenario-stress@example.com")
    account = create_account(client, headers)
    buy_position(client, headers, account["id"], symbol="LFTEST", quantity="10", price="100")

    stress = client.post(
        f"/api/v1/market-simulator/portfolio/{account['id']}/stress",
        headers=headers,
        json={"scenario_name": "inflation_shock", "steps": 30, "seed": 7},
    )
    assert stress.status_code == 200
    body = stress.json()
    assert body["account_id"] == account["id"]
    assert body["scenario_name"] == "inflation_shock"
    assert body["starting_equity"] == "10000.00"
    assert len(body["positions"]) == 1
    assert body["positions"][0]["symbol"] == "LFTEST"

    portfolio = client.get(
        f"/api/v1/market-simulator/portfolio/{account['id']}",
        headers=headers,
    )
    assert portfolio.status_code == 200
    assert portfolio.json()["positions"][0]["last_price"] == "100.000000"
    assert portfolio.json()["total_equity"] == "10000.00"


def test_portfolio_stress_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="scenario-owner@example.com")
    other_headers = auth_headers(client, email="scenario-other@example.com")
    account = create_account(client, owner_headers)

    response = client.post(
        f"/api/v1/market-simulator/portfolio/{account['id']}/stress",
        headers=other_headers,
        json={"scenario_name": "bull_market", "steps": 10, "seed": 1},
    )
    assert response.status_code == 404
