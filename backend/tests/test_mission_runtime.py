from tests.conftest import auth_headers


def create_project(client, headers, title="Mission project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Complete an auditable research mission"},
    )
    assert response.status_code == 201
    return response.json()


def create_mission(client, headers, project_id):
    response = client.post(
        "/api/v1/missions",
        headers=headers,
        json={
            "project_id": project_id,
            "title": "Validate mission objective",
            "objective": "Reach a traceable evidence-backed recommendation",
            "success_criteria": ["Evidence reviewed", "Executive snapshot persisted"],
        },
    )
    assert response.status_code == 201
    return response.json()


def create_approved_evidence(client, headers, project_id, index=1):
    created = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://mission{index}.example.com/report",
            "source_title": f"Mission report {index}",
            "publisher": f"Mission Institute {index}",
            "author": f"Reviewer {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": f"Mission evidence finding {index}",
            "excerpt": f"Documented mission evidence {index}",
            "stance": "supports",
        },
    )
    assert created.status_code == 201
    evidence = created.json()
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Verified for mission"},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def test_mission_blocks_without_evidence_then_retries(client):
    headers = auth_headers(client, email="mission-block@example.com")
    project = create_project(client, headers)
    mission = create_mission(client, headers, project["id"])
    url = f"/api/v1/missions/{mission['id']}/advance"

    first = client.post(url, headers=headers)
    assert first.status_code == 200
    assert first.json()["current_step_order"] == 1

    blocked = client.post(url, headers=headers)
    assert blocked.status_code == 200
    body = blocked.json()
    assert body["status"] == "blocked"
    blocked_step = next(item for item in body["steps"] if item["status"] == "blocked")
    assert "evidence" in blocked_step["blocking_reason"].lower()

    create_approved_evidence(client, headers, project["id"])
    retry = client.post(
        f"/api/v1/missions/{mission['id']}/steps/{blocked_step['id']}/retry",
        headers=headers,
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "running"

    advanced = client.post(url, headers=headers)
    assert advanced.status_code == 200
    assert advanced.json()["current_step_order"] == 2


def test_mission_completes_with_final_snapshot_and_is_idempotent(client):
    headers = auth_headers(client, email="mission-complete@example.com")
    project = create_project(client, headers, "Completed mission project")
    evidence = create_approved_evidence(client, headers, project["id"], 10)
    mission = create_mission(client, headers, project["id"])
    url = f"/api/v1/missions/{mission['id']}/advance"

    body = mission
    for _ in range(7):
        response = client.post(url, headers=headers)
        assert response.status_code == 200
        body = response.json()

    assert body["status"] == "completed"
    assert body["current_step_order"] == 7
    assert body["final_snapshot_id"] is not None
    assert all(step["status"] == "completed" for step in body["steps"])
    validation_step = next(step for step in body["steps"] if step["key"] == "validate_evidence")
    assert evidence["id"] in validation_step["outputs"]["approved_evidence_ids"]

    repeated = client.post(url, headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["final_snapshot_id"] == body["final_snapshot_id"]
    assert len(repeated.json()["steps"]) == 7


def test_mission_can_be_cancelled(client):
    headers = auth_headers(client, email="mission-cancel@example.com")
    project = create_project(client, headers, "Cancelled mission project")
    mission = create_mission(client, headers, project["id"])

    response = client.post(f"/api/v1/missions/{mission['id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_mission_access_is_owner_isolated(client):
    owner_headers = auth_headers(client, email="mission-owner@example.com")
    project = create_project(client, owner_headers, "Private mission project")
    mission = create_mission(client, owner_headers, project["id"])

    other_headers = auth_headers(client, email="mission-other@example.com")
    assert client.get(
        f"/api/v1/missions/{mission['id']}", headers=other_headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/missions/{mission['id']}/advance", headers=other_headers
    ).status_code == 404
