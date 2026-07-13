from tests.conftest import auth_headers


def create_project(client, headers, title):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Federate durable research knowledge"},
    )
    assert response.status_code == 201
    return response.json()


def create_approved_evidence(client, headers, project_id, claim, index):
    created = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://federation{index}.example.com/report",
            "source_title": f"Federation report {index}",
            "publisher": "Federation Institute",
            "author": "Research Reviewer",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": claim,
            "excerpt": claim,
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


def complete_and_promote(client, headers, project_id, title):
    mission_response = client.post(
        "/api/v1/missions",
        headers=headers,
        json={
            "project_id": project_id,
            "title": title,
            "objective": "Produce reusable federated knowledge",
            "success_criteria": ["Snapshot persisted"],
        },
    )
    assert mission_response.status_code == 201
    mission = mission_response.json()
    for _ in range(7):
        response = client.post(
            f"/api/v1/missions/{mission['id']}/advance",
            headers=headers,
        )
        assert response.status_code == 200
        mission = response.json()
    promoted = client.post(
        f"/api/v1/knowledge-memory/projects/{project_id}/promote-mission/{mission['id']}",
        headers=headers,
    )
    assert promoted.status_code == 200
    return promoted.json()["memories"]


def prepare_two_projects(client, headers):
    claim = "Shared infrastructure reduces research duplication"
    first = create_project(client, headers, "Federation Alpha")
    second = create_project(client, headers, "Federation Beta")
    create_approved_evidence(client, headers, first["id"], claim, 1)
    create_approved_evidence(client, headers, second["id"], claim, 2)
    first_memories = complete_and_promote(client, headers, first["id"], "Alpha mission")
    second_memories = complete_and_promote(client, headers, second["id"], "Beta mission")
    return first, second, first_memories, second_memories


def test_scan_detects_duplicate_and_reuses_existing_link(client):
    headers = auth_headers(client, email="federation@example.com")
    first, _, _, _ = prepare_two_projects(client, headers)
    url = f"/api/v1/knowledge-federation/projects/{first['id']}/scan"

    initial = client.post(url, headers=headers)
    repeated = client.post(url, headers=headers)

    assert initial.status_code == 200
    assert repeated.status_code == 200
    assert initial.json()["created_count"] >= 1
    assert repeated.json()["created_count"] == 0
    assert repeated.json()["reused_count"] == len(initial.json()["links"])
    assert any(link["link_type"] == "duplicate" for link in initial.json()["links"])
    assert all(
        link["provenance"]["methodology_version"] == "knowledge-federation-v1"
        for link in initial.json()["links"]
    )


def test_contradiction_preserved_and_review_creates_revision(client):
    headers = auth_headers(client, email="federation-review@example.com")
    first, _, first_memories, second_memories = prepare_two_projects(client, headers)
    first_fact = next(item for item in first_memories if item["category"] == "verified_fact")
    second_fact = next(item for item in second_memories if item["category"] == "verified_fact")

    changed = client.patch(
        f"/api/v1/knowledge-memory/{second_fact['id']}",
        headers=headers,
        json={"status": "contested"},
    )
    assert changed.status_code == 200

    scan = client.post(
        f"/api/v1/knowledge-federation/projects/{first['id']}/scan",
        headers=headers,
    )
    assert scan.status_code == 200
    contradiction = next(
        link
        for link in scan.json()["links"]
        if {link["source_memory_id"], link["target_memory_id"]}
        == {first_fact["id"], second_fact["id"]}
    )
    assert contradiction["link_type"] == "contradicting"

    reviewed = client.patch(
        f"/api/v1/knowledge-federation/{contradiction['id']}",
        headers=headers,
        json={"status": "accepted"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["revision_number"] == 2
    assert len(reviewed.json()["revisions"]) == 2


def test_filters_synthesis_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="federation-owner@example.com")
    first, _, _, _ = prepare_two_projects(client, owner_headers)
    scan = client.post(
        f"/api/v1/knowledge-federation/projects/{first['id']}/scan",
        headers=owner_headers,
    )
    assert scan.status_code == 200
    link = scan.json()["links"][0]

    filtered = client.get(
        f"/api/v1/knowledge-federation?project_id={first['id']}&link_type={link['link_type']}",
        headers=owner_headers,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == link["id"] for item in filtered.json())

    synthesis = client.get("/api/v1/knowledge-federation/synthesis", headers=owner_headers)
    assert synthesis.status_code == 200
    assert synthesis.json()["total_links"] >= 1

    other_headers = auth_headers(client, email="federation-other@example.com")
    assert client.get(
        f"/api/v1/knowledge-federation/{link['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/knowledge-federation/projects/{first['id']}/related",
        headers=other_headers,
    ).status_code == 404
