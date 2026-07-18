from tests.conftest import auth_headers


def create_project(client, headers, title):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Inspect and control personal memory"},
    )
    assert response.status_code == 201
    return response.json()


def create_memory(client, headers, project_id, category="learning_goal"):
    response = client.post(
        "/api/v1/knowledge-memory/user-authored",
        headers=headers,
        json={
            "project_id": project_id,
            "statement": "Master source evaluation",
            "summary": "Prioritize source evaluation practice",
            "category": category,
            "confidence": 0.4,
            "source_evidence_ids": [],
            "provenance": {"basis": "User preference"},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_control_summary_counts_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="memory-summary-owner@example.com")
    project = create_project(client, owner_headers, "Summary project")
    first = create_memory(client, owner_headers, project["id"])
    create_memory(client, owner_headers, project["id"], "mentor_preference")

    revised = client.patch(
        f"/api/v1/knowledge-memory/{first['id']}",
        headers=owner_headers,
        json={"summary": "Practice evaluating primary sources first"},
    )
    assert revised.status_code == 200
    archived = client.post(
        f"/api/v1/knowledge-memory/{first['id']}/archive",
        headers=owner_headers,
    )
    assert archived.status_code == 200

    summary = client.get(
        f"/api/v1/knowledge-memory/controls/summary?project_id={project['id']}",
        headers=owner_headers,
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["project_id"] == project["id"]
    assert body["total_count"] == 2
    assert body["active_count"] == 1
    assert body["archived_count"] == 1
    assert body["user_authored_count"] == 2
    assert body["research_generated_count"] == 0
    assert body["revision_count"] == 4
    assert body["by_status"] == {"archived": 1, "provisional": 1}
    assert body["by_category"] == {"learning_goal": 1, "mentor_preference": 1}
    assert set(body["available_controls"]) == {
        "inspect",
        "revise",
        "archive",
        "restore",
        "delete",
        "supersede",
        "recover_version",
    }

    other_headers = auth_headers(client, email="memory-summary-other@example.com")
    denied = client.get(
        f"/api/v1/knowledge-memory/controls/summary?project_id={project['id']}",
        headers=other_headers,
    )
    assert denied.status_code == 404

    empty = client.get("/api/v1/knowledge-memory/controls/summary", headers=other_headers)
    assert empty.status_code == 200
    assert empty.json()["total_count"] == 0
