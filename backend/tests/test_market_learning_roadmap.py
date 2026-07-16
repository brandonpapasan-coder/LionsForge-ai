from tests.conftest import auth_headers
from tests.test_market_learning_portfolio import create_account, create_project, create_session, submit_evidence


def test_learning_roadmap_not_started_and_owner_scoped(client):
    first_headers = auth_headers(client, email="roadmap-first@example.com")
    second_headers = auth_headers(client, email="roadmap-second@example.com")
    account = create_account(client, first_headers)
    create_session(client, first_headers, account["id"], "bear_market", 101)

    first = client.get("/api/v1/market-simulator/learning-roadmap", headers=first_headers)
    second = client.get("/api/v1/market-simulator/learning-roadmap", headers=second_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "active"
    assert second.json()["status"] == "not_started"
    assert all(task.get("session_id") is None for task in second.json()["tasks"])


def test_learning_roadmap_orders_unresolved_then_unsubmitted_then_coverage(client):
    headers = auth_headers(client, email="roadmap-order@example.com")
    project = create_project(client, headers, title="Roadmap project")
    account = create_account(client, headers)
    reviewed_session = create_session(client, headers, account["id"], "bear_market", 201)
    unsubmitted = create_session(client, headers, account["id"], "high_volatility", 202)
    evidence = submit_evidence(
        client,
        headers,
        reviewed_session["id"],
        project["id"],
        "The simulated exercise suggested concentration increased modeled downside under the selected assumptions.",
    )
    review = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['evidence']['id']}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Compare another scenario."},
    )
    assert review.status_code == 200

    response = client.get("/api/v1/market-simulator/learning-roadmap", headers=headers)
    assert response.status_code == 200
    body = response.json()
    priorities = [task["priority"] for task in body["tasks"]]
    assert priorities == sorted(priorities)
    assert body["tasks"][0]["task_type"] == "resolve_evidence"
    assert any(task["task_type"] == "submit_evidence" and task["session_id"] == unsubmitted["id"] for task in body["tasks"])
    assert any(task["task_type"] == "explore_scenario" for task in body["tasks"])
    assert "Simulated returns are excluded" in " ".join(body["calculation_criteria"])
    assert "does not provide investment recommendations" in body["disclaimer"]
