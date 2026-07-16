from tests.conftest import auth_headers


def create_project(client, headers, title="Simulation evidence project"):
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
        json={"name": "Evidence simulator", "starting_cash": "10000.00"},
    )
    assert response.status_code == 201
    return response.json()


def create_session(client, headers, account_id):
    response = client.post(
        "/api/v1/market-simulator/learning-sessions",
        headers=headers,
        json={
            "account_id": account_id,
            "scenario_name": "bear_market",
            "steps": 20,
            "seed": 17,
            "learner_reflection": "I observed that concentration increased simulated downside and that the cash buffer reduced the modeled loss.",
        },
    )
    assert response.status_code == 201
    return response.json()


def evidence_payload(session_id, project_id):
    return {
        "session_id": session_id,
        "project_id": project_id,
        "claim": "The simulated bear-market exercise demonstrated that concentration amplified modeled downside risk.",
        "stance": "supports",
        "contradiction_key": "concentration-downside",
    }


def test_completed_session_becomes_segregated_learning_evidence(client):
    headers = auth_headers(client, email="learning-evidence@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    session = create_session(client, headers, account["id"])

    response = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=headers,
        json=evidence_payload(session["id"], project["id"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classification"] == "simulated_educational_evidence"
    assert body["evidence"]["source_type"] == "user"
    assert body["evidence"]["validation_status"] == "unverified"
    assert body["evidence"]["provenance"]["excluded_from_empirical_evidence"] is True
    assert body["evidence"]["provenance"]["market_learning_session_id"] == session["id"]
    assert "not real-world empirical evidence" in body["disclaimer"]


def test_learning_evidence_prevents_duplicate_session_conversion(client):
    headers = auth_headers(client, email="learning-evidence-duplicate@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    session = create_session(client, headers, account["id"])
    payload = evidence_payload(session["id"], project["id"])

    assert client.post("/api/v1/market-simulator/learning-evidence", headers=headers, json=payload).status_code == 201
    duplicate = client.post("/api/v1/market-simulator/learning-evidence", headers=headers, json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["message"] == "Learning session already converted to evidence"


def test_learning_evidence_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="learning-evidence-owner@example.com")
    other_headers = auth_headers(client, email="learning-evidence-other@example.com")
    project = create_project(client, owner_headers)
    account = create_account(client, owner_headers)
    session = create_session(client, owner_headers, account["id"])

    hidden_session = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=other_headers,
        json=evidence_payload(session["id"], project["id"]),
    )
    assert hidden_session.status_code == 404

    other_project = create_project(client, other_headers, title="Other project")
    hidden_project = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=owner_headers,
        json=evidence_payload(session["id"], other_project["id"]),
    )
    assert hidden_project.status_code == 404


def test_learning_evidence_surfaces_immutable_review_history(client):
    headers = auth_headers(client, email="learning-evidence-review@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    session = create_session(client, headers, account["id"])
    created = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=headers,
        json=evidence_payload(session["id"], project["id"]),
    )
    assert created.status_code == 201
    evidence_id = created.json()["evidence"]["id"]

    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence_id}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Compare another scenario before accepting the interpretation."},
    )
    assert reviewed.status_code == 200

    history = client.get(
        f"/api/v1/market-simulator/learning-evidence/{session['id']}",
        headers=headers,
    )
    assert history.status_code == 200
    body = history.json()
    assert body["evidence"]["evidence"]["validation_status"] == "needs_review"
    assert body["reviews"][0]["previous_status"] == "unverified"
    assert body["reviews"][0]["validation_status"] == "needs_review"
    assert "additional scenario" in body["evidence"]["next_reflection_prompt"]


def test_learning_evidence_does_not_mutate_simulation_portfolio(client):
    headers = auth_headers(client, email="learning-evidence-immutable@example.com")
    project = create_project(client, headers)
    account = create_account(client, headers)
    session = create_session(client, headers, account["id"])
    before = client.get(f"/api/v1/market-simulator/accounts/{account['id']}", headers=headers)
    assert before.status_code == 200

    created = client.post(
        "/api/v1/market-simulator/learning-evidence",
        headers=headers,
        json=evidence_payload(session["id"], project["id"]),
    )
    assert created.status_code == 201
    after = client.get(f"/api/v1/market-simulator/accounts/{account['id']}", headers=headers)
    assert after.status_code == 200
    assert after.json()["cash_balance"] == before.json()["cash_balance"]
    assert after.json()["positions"] == before.json()["positions"]
