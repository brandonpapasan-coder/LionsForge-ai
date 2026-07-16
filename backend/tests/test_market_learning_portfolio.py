from tests.conftest import auth_headers


def create_project(client, headers, title="Learning portfolio project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Review simulated learning evidence"},
    )
    assert response.status_code == 201
    return response.json()


def create_account(client, headers):
    response = client.post(
        "/api/v1/market-simulator/accounts",
        headers=headers,
        json={"name": "Portfolio simulator", "starting_cash": "10000.00"},
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
            "learner_reflection": "I compared modeled downside, concentration, and cash-buffer behavior in this educational scenario.",
        },
    )
    assert response.status_code == 201
    return response.json()


def submit_evidence(client, headers, session_id, project_id, claim):
    response = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=headers,
        json={
            "session_id": session_id,
            "project_id": project_id,
            "claim": claim,
            "stance": "supports",
            "contradiction_key": "portfolio-learning",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_market_learning_portfolio_empty_state(client):
    headers = auth_headers(client, email="portfolio-empty@example.com")
    response = client.get("/api/v1/market-simulator/learning-portfolio", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["completed_sessions"] == 0
    assert body["submitted_evidence"] == 0
    assert body["immutable_review_events"] == 0
    assert body["learning_maturity"] == "not_started"
    assert body["recent_claims"] == []
    assert "not a record of investment performance" in body["disclaimer"]


def test_market_learning_portfolio_summarizes_sessions_and_evidence(client):
    headers = auth_headers(client, email="portfolio-summary@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    first = create_session(client, headers, account["id"], "bear_market", 11)
    second = create_session(client, headers, account["id"], "high_volatility", 12)
    evidence = submit_evidence(
        client,
        headers,
        first["id"],
        project["id"],
        "The simulated bear-market exercise indicated that concentration amplified modeled downside risk.",
    )

    response = client.get("/api/v1/market-simulator/learning-portfolio", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["completed_sessions"] == 2
    assert body["unique_scenarios"] == 2
    assert body["scenario_counts"] == {"bear_market": 1, "high_volatility": 1}
    assert sum(body["risk_tier_counts"].values()) == 2
    assert body["submitted_evidence"] == 1
    assert body["validation_status_counts"] == {"unverified": 1}
    assert body["learning_maturity"] == "foundational"
    assert body["recent_claims"][0]["evidence_id"] == evidence["evidence"]["id"]
    assert body["recent_claims"][0]["review_event_count"] == 0


def test_market_learning_portfolio_aggregates_immutable_reviews(client):
    headers = auth_headers(client, email="portfolio-reviews@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    session = create_session(client, headers, account["id"], "inflation_shock", 21)
    evidence = submit_evidence(
        client,
        headers,
        session["id"],
        project["id"],
        "The simulated inflation shock highlighted sensitivity to modeled rate and valuation assumptions.",
    )
    evidence_id = evidence["evidence"]["id"]
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence_id}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Compare another inflation-sensitive scenario."},
    )
    assert reviewed.status_code == 200

    response = client.get("/api/v1/market-simulator/learning-portfolio", headers=headers)
    body = response.json()
    assert body["immutable_review_events"] == 1
    assert body["validation_status_counts"] == {"needs_review": 1}
    claim = body["recent_claims"][0]
    assert claim["review_event_count"] == 1
    assert claim["reviewer_notes"] == "Compare another inflation-sensitive scenario."
    assert "additional scenario" in claim["next_reflection_prompt"]


def test_market_learning_portfolio_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="portfolio-owner@example.com")
    other_headers = auth_headers(client, email="portfolio-other@example.com")
    project = create_project(client, owner_headers)
    account = create_account(client, owner_headers)
    session = create_session(client, owner_headers, account["id"], "bull_market", 31)
    submit_evidence(
        client,
        owner_headers,
        session["id"],
        project["id"],
        "The simulated bull-market exercise showed how favorable assumptions can mask concentration risk.",
    )

    response = client.get("/api/v1/market-simulator/learning-portfolio", headers=other_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["completed_sessions"] == 0
    assert body["submitted_evidence"] == 0
    assert body["recent_claims"] == []
