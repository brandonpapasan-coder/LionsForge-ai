from tests.conftest import auth_headers
from tests.test_market_learning_portfolio import create_account, create_project, create_session, submit_evidence


def test_market_learning_mastery_not_started_and_owner_scoped(client):
    first_headers = auth_headers(client, email="mastery-first@example.com")
    second_headers = auth_headers(client, email="mastery-second@example.com")
    account = create_account(client, first_headers)
    create_session(client, first_headers, account["id"], "bear_market", 301)

    first = client.get("/api/v1/market-simulator/learning-mastery", headers=first_headers)
    second = client.get("/api/v1/market-simulator/learning-mastery", headers=second_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["overall_readiness"] == "foundational"
    assert second.json()["overall_readiness"] == "not_started"
    assert all(dimension["evidence_count"] == 0 for dimension in second.json()["dimensions"])


def test_market_learning_mastery_uses_deterministic_non_return_rubric(client):
    headers = auth_headers(client, email="mastery-rubric@example.com")
    account = create_account(client, headers)
    create_session(client, headers, account["id"], "bear_market", 311)
    create_session(client, headers, account["id"], "bull_market", 312)
    create_session(client, headers, account["id"], "high_volatility", 313)
    create_session(client, headers, account["id"], "inflation_shock", 314)

    response = client.get("/api/v1/market-simulator/learning-mastery", headers=headers)
    assert response.status_code == 200
    body = response.json()
    dimensions = {dimension["key"]: dimension for dimension in body["dimensions"]}
    assert dimensions["scenario_breadth"]["status"] == "met"
    assert dimensions["reflection_quality"]["status"] == "developing"
    assert "Simulated returns" in " ".join(body["calculation_criteria"])
    assert "investment-performance evidence" in body["disclaimer"]


def test_market_learning_mastery_counts_evidence_and_review_follow_through(client):
    headers = auth_headers(client, email="mastery-review@example.com")
    project = create_project(client, headers, title="Mastery review project")
    account = create_account(client, headers)
    sessions = [
        create_session(client, headers, account["id"], scenario, 320 + index)
        for index, scenario in enumerate(("bear_market", "bull_market", "high_volatility"))
    ]
    evidence_records = [
        submit_evidence(
            client,
            headers,
            session["id"],
            project["id"],
            f"The simulated {session['scenario_name']} session supported a bounded comparison under stated assumptions {index}.",
        )["evidence"]
        for index, session in enumerate(sessions)
    ]
    for evidence in evidence_records:
        review = client.patch(
            f"/api/v1/evidence-intelligence/{evidence['id']}/review",
            headers=headers,
            json={"validation_status": "approved", "reviewer_notes": "Scope and limitations reviewed."},
        )
        assert review.status_code == 200

    response = client.get("/api/v1/market-simulator/learning-mastery", headers=headers)
    assert response.status_code == 200
    dimensions = {dimension["key"]: dimension for dimension in response.json()["dimensions"]}
    assert dimensions["evidence_discipline"]["evidence_count"] == 3
    assert dimensions["review_follow_through"]["status"] == "met"
    assert dimensions["review_follow_through"]["evidence_count"] == 3
