from tests.conftest import auth_headers


def create_account(client, headers):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": "Progress portfolio", "starting_cash": "10000.00"},
    )
    assert response.status_code == 201
    return response.json()


def create_session(client, headers, account_id, scenario_name, seed):
    response = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=headers,
        json={
            "account_id": account_id,
            "scenario_name": scenario_name,
            "steps": 20,
            "seed": seed,
            "learner_reflection": "I compared the simulated portfolio response and identified how cash and concentration changed the outcome.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_learning_progress_starts_empty(client):
    headers = auth_headers(client, email="progress-empty@example.com")
    response = client.get("/api/v1/market-simulator/learning-progress", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_sessions"] == 0
    assert body["proficiency_level"] == "not_started"
    assert body["evidence_badge_eligible"] is False
    assert "not" in body["disclaimer"].lower()


def test_learning_progress_aggregates_owner_sessions(client):
    headers = auth_headers(client, email="progress-owner@example.com")
    account = create_account(client, headers)
    create_session(client, headers, account["id"], "bull_market", 1)
    create_session(client, headers, account["id"], "bear_market", 2)
    create_session(client, headers, account["id"], "high_volatility", 3)

    response = client.get("/api/v1/market-simulator/learning-progress", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_sessions"] == 3
    assert body["completed_sessions"] == 3
    assert body["unique_scenarios"] == 3
    assert body["scenario_counts"] == {
        "bear_market": 1,
        "bull_market": 1,
        "high_volatility": 1,
    }
    assert sum(body["risk_tier_counts"].values()) == 3
    assert body["proficiency_level"] == "developing"
    assert body["latest_completed_at"]


def test_learning_progress_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="progress-private-owner@example.com")
    other_headers = auth_headers(client, email="progress-private-other@example.com")
    account = create_account(client, owner_headers)
    create_session(client, owner_headers, account["id"], "inflation_shock", 7)

    response = client.get("/api/v1/market-simulator/learning-progress", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["total_sessions"] == 0
