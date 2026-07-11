from tests.conftest import auth_headers


def test_dashboard_requires_authentication(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_dashboard_returns_empty_state(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["greeting"].startswith("Welcome back")
    assert {metric["label"]: metric["value"] for metric in payload["metrics"]} == {
        "Active projects": 0,
        "Active sessions": 0,
        "Mentor conversations": 0,
    }
    assert payload["next_actions"][0]["href"] == "/research/new"
    assert payload["recent_activity"] == []


def test_dashboard_aggregates_research_and_mentor_activity(client):
    headers = auth_headers(client)

    project = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={
            "title": "Semiconductor research",
            "description": "Evaluate industry structure",
            "objective": "Identify durable competitive advantages",
            "context": {"sector": "technology"},
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    session = client.post(
        f"/api/v1/research-projects/{project_id}/sessions",
        headers=headers,
        json={
            "title": "Evidence review",
            "objective": "Review primary sources",
            "context": {"stage": "evidence"},
        },
    )
    assert session.status_code == 201

    mentor = client.post(
        "/api/v1/mentor/chat",
        headers=headers,
        json={"message": "Challenge the evidence in my semiconductor research"},
    )
    assert mentor.status_code == 201

    response = client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    metrics = {metric["label"]: metric["value"] for metric in payload["metrics"]}
    assert metrics == {
        "Active projects": 1,
        "Active sessions": 1,
        "Mentor conversations": 1,
    }
    assert payload["next_actions"][0]["href"] == "/research"
    assert {item["kind"] for item in payload["recent_activity"]} == {"research", "mentor"}
