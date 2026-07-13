from tests.conftest import auth_headers


def create_project(client, headers, title="Memory project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Build durable research memory"},
    )
    assert response.status_code == 201
    return response.json()


def create_approved_evidence(client, headers, project_id, index=1):
    created = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://memory{index}.example.com/report",
            "source_title": f"Memory report {index}",
            "publisher": f"Memory Institute {index}",
            "author": f"Reviewer {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": f"Memory finding {index}",
            "excerpt": f"Documented memory evidence {index}",
            "stance": "supports",
        },
    )
    assert created.status_code == 201
    evidence = created.json()
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Verified"},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def complete_mission(client, headers, project_id):
    created = client.post(
        "/api/v1/missions",
        headers=headers,
        json={
            "project_id": project_id,
            "title": "Memory mission",
            "objective": "Produce reusable knowledge",
            "success_criteria": ["Snapshot persisted"],
        },
    )
    assert created.status_code == 201
    mission = created.json()
    for _ in range(7):
        response = client.post(f"/api/v1/missions/{mission['id']}/advance", headers=headers)
        assert response.status_code == 200
        mission = response.json()
    assert mission["status"] == "completed"
    return mission


def test_completed_mission_promotes_once_and_preserves_provenance(client):
    headers = auth_headers(client, email="memory@example.com")
    project = create_project(client, headers)
    evidence = create_approved_evidence(client, headers, project["id"])
    mission = complete_mission(client, headers, project["id"])
    url = f"/api/v1/knowledge-memory/projects/{project['id']}/promote-mission/{mission['id']}"

    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created_count"] >= 1
    assert second.json()["created_count"] == 0
    assert second.json()["reused_count"] == len(first.json()["memories"])
    memory = first.json()["memories"][0]
    assert memory["mission_id"] == mission["id"]
    assert memory["snapshot_id"] == mission["final_snapshot_id"]
    assert evidence["id"] in memory["source_evidence_ids"]
    assert memory["provenance"]["memory_methodology_version"] == "knowledge-memory-v1"
    assert len(memory["revisions"]) == 1


def test_memory_update_creates_immutable_revision_and_filters(client):
    headers = auth_headers(client, email="memory-revision@example.com")
    project = create_project(client, headers, "Revision project")
    create_approved_evidence(client, headers, project["id"], 10)
    mission = complete_mission(client, headers, project["id"])
    promoted = client.post(
        f"/api/v1/knowledge-memory/projects/{project['id']}/promote-mission/{mission['id']}",
        headers=headers,
    ).json()
    memory = promoted["memories"][0]

    updated = client.patch(
        f"/api/v1/knowledge-memory/{memory['id']}",
        headers=headers,
        json={"summary": "Human-reviewed durable conclusion", "confidence": 0.9},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["revision_number"] == 2
    assert len(body["revisions"]) == 2
    assert body["revisions"][0]["summary"] != body["revisions"][1]["summary"]

    filtered = client.get(
        f"/api/v1/knowledge-memory?project_id={project['id']}&query=durable",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == memory["id"] for item in filtered.json())


def test_memory_synthesis_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="memory-owner@example.com")
    project = create_project(client, owner_headers, "Private memory project")
    create_approved_evidence(client, owner_headers, project["id"], 20)
    mission = complete_mission(client, owner_headers, project["id"])
    promoted = client.post(
        f"/api/v1/knowledge-memory/projects/{project['id']}/promote-mission/{mission['id']}",
        headers=owner_headers,
    ).json()
    memory_id = promoted["memories"][0]["id"]

    synthesis = client.get(
        f"/api/v1/knowledge-memory/projects/{project['id']}/synthesis",
        headers=owner_headers,
    )
    assert synthesis.status_code == 200
    assert synthesis.json()["project_id"] == project["id"]

    other_headers = auth_headers(client, email="memory-other@example.com")
    assert client.get(
        f"/api/v1/knowledge-memory/{memory_id}", headers=other_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/knowledge-memory/projects/{project['id']}/synthesis",
        headers=other_headers,
    ).status_code == 404
