from tests.conftest import auth_headers


def create_project(client, headers, title="Planning Project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Generate an auditable research roadmap"},
    )
    assert response.status_code == 201
    return response.json()


def create_approved_evidence(client, headers, project_id, claim):
    created = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": "https://planning.example.com/report",
            "source_title": "Planning report",
            "publisher": "Planning Institute",
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


def complete_and_promote(client, headers, project_id, claim):
    create_approved_evidence(client, headers, project_id, claim)
    mission_response = client.post(
        "/api/v1/missions",
        headers=headers,
        json={
            "project_id": project_id,
            "title": "Planning source mission",
            "objective": "Produce durable knowledge",
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


def test_generation_is_ranked_and_deterministic(client):
    headers = auth_headers(client, email="planning@example.com")
    project = create_project(client, headers)
    memories = complete_and_promote(
        client,
        headers,
        project["id"],
        "Independent validation improves research confidence",
    )
    memory = memories[0]
    contested = client.patch(
        f"/api/v1/knowledge-memory/{memory['id']}",
        headers=headers,
        json={"status": "contested", "confidence": 0.45},
    )
    assert contested.status_code == 200

    url = f"/api/v1/research-planning/projects/{project['id']}/generate"
    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["created_count"] >= 1
    assert second_payload["created_count"] == 0
    assert second_payload["reused_count"] == len(first_payload["recommendations"])
    scores = [item["priority_score"] for item in first_payload["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    assert any(
        item["recommendation_type"] == "contradiction_resolution"
        for item in first_payload["recommendations"]
    )
    assert all(
        item["provenance"]["methodology_version"] == "research-planning-v1"
        for item in first_payload["recommendations"]
    )


def test_review_revision_and_safe_mission_draft_conversion(client):
    headers = auth_headers(client, email="planning-mission@example.com")
    project = create_project(client, headers, "Mission Planning")
    complete_and_promote(
        client,
        headers,
        project["id"],
        "Research planning should remain advisory",
    )
    generated = client.post(
        f"/api/v1/research-planning/projects/{project['id']}/generate",
        headers=headers,
    )
    assert generated.status_code == 200
    recommendation = generated.json()["recommendations"][0]

    blocked = client.post(
        f"/api/v1/research-planning/{recommendation['id']}/create-mission-draft",
        headers=headers,
    )
    assert blocked.status_code == 409

    accepted = client.patch(
        f"/api/v1/research-planning/{recommendation['id']}",
        headers=headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["revision_number"] == 2
    assert len(accepted.json()["revisions"]) == 2

    created = client.post(
        f"/api/v1/research-planning/{recommendation['id']}/create-mission-draft",
        headers=headers,
    )
    repeated = client.post(
        f"/api/v1/research-planning/{recommendation['id']}/create-mission-draft",
        headers=headers,
    )
    assert created.status_code == 200
    assert repeated.status_code == 200
    assert created.json()["id"] == repeated.json()["id"]
    assert created.json()["status"] == "draft"
    assert created.json()["current_step_order"] == 0


def test_filters_roadmap_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="planning-owner@example.com")
    project = create_project(client, owner_headers, "Owner Planning")
    complete_and_promote(
        client,
        owner_headers,
        project["id"],
        "Roadmaps should preserve recommendation states",
    )
    generated = client.post(
        f"/api/v1/research-planning/projects/{project['id']}/generate",
        headers=owner_headers,
    )
    assert generated.status_code == 200
    recommendation = generated.json()["recommendations"][0]

    filtered = client.get(
        f"/api/v1/research-planning?project_id={project['id']}&recommendation_type={recommendation['recommendation_type']}",
        headers=owner_headers,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == recommendation["id"] for item in filtered.json())

    roadmap = client.get(
        f"/api/v1/research-planning/projects/{project['id']}/roadmap",
        headers=owner_headers,
    )
    assert roadmap.status_code == 200
    assert roadmap.json()["total_recommendations"] >= 1
    assert roadmap.json()["top_priorities"]

    other_headers = auth_headers(client, email="planning-other@example.com")
    assert client.get(
        f"/api/v1/research-planning/{recommendation['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/research-planning/projects/{project['id']}/roadmap",
        headers=other_headers,
    ).status_code == 404
