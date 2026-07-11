from tests.conftest import auth_headers


def test_critical_user_journey(client):
    headers = auth_headers(client, email="release-user@example.com")

    dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]

    project = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={
            "title": "Release readiness research",
            "description": "Validate the full LionsForge workflow",
            "objective": "Confirm the critical user journey",
            "context": {
                "notebook": {
                    "thesis": "The integrated workflow is operational.",
                    "evidence": "Each protected API returns expected state.",
                    "risks": "Migration or context persistence failures.",
                    "decision_journal": "Proceed only when all gates pass.",
                }
            },
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    session = client.post(
        f"/api/v1/research-projects/{project_id}/sessions",
        headers=headers,
        json={
            "title": "Acceptance review",
            "objective": "Challenge release assumptions",
            "context": {"stage": "acceptance"},
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    mentor = client.post(
        "/api/v1/mentor/chat",
        headers=headers,
        json={
            "message": "Challenge the evidence and release assumptions in this project",
            "context": {
                "research_project_id": project_id,
                "research_session_id": session_id,
            },
        },
    )
    assert mentor.status_code == 201
    conversation_id = mentor.json()["conversation_id"]

    history = client.get(
        f"/api/v1/mentor/conversations/{conversation_id}",
        headers=headers,
    )
    assert history.status_code == 200
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]
    assert history.json()["active_context"]["research_project"]["id"] == project_id
    assert history.json()["active_context"]["research_session"]["id"] == session_id

    education = client.get("/api/v1/education", headers=headers)
    assert education.status_code == 200
    assert education.json()["total_lessons"] > 0

    lesson_slug = education.json()["lessons"][0]["slug"]
    completed = client.put(
        f"/api/v1/education/lessons/{lesson_slug}/progress",
        headers=headers,
        json={"status": "completed", "score": 100},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_lessons"] == 1

    refreshed_dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert refreshed_dashboard.status_code == 200
    metrics = {item["label"]: item["value"] for item in refreshed_dashboard.json()["metrics"]}
    assert metrics["Active projects"] == 1
    assert metrics["Active sessions"] == 1
    assert metrics["Mentor conversations"] == 1
