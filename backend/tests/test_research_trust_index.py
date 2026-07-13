from tests.conftest import auth_headers


def create_project(client, headers, title="RTI project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Measure research trust"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index, stance="supports", key=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://source{index}.example.com/report",
            "source_title": f"Research report {index}",
            "publisher": f"Institute {index}",
            "author": f"Researcher {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary" if index % 2 else "official",
            "claim": f"Finding {index} supports the mission conclusion.",
            "excerpt": f"Independent measurement {index} produced a documented result.",
            "stance": stance,
            "contradiction_key": key,
            "provenance": {"test_source": index},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_project_rti_explains_components_and_recommendations(client):
    headers = auth_headers(client, email="rti@example.com")
    project = create_project(client, headers)

    first = create_evidence(client, headers, project["id"], 1, key="mission-outcome")
    for index in range(2, 6):
        create_evidence(client, headers, project["id"], index, key="mission-outcome")

    review = client.patch(
        f"/api/v1/evidence-intelligence/{first['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Reviewed against source"},
    )
    assert review.status_code == 200

    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["evidence_count"] == 5
    assert body["supporting_count"] == 5
    assert body["approved_count"] == 1
    assert body["methodology_version"] == "rti-v1"
    assert 0 <= body["overall_score"] <= 100
    assert len(body["components"]) == 6
    assert {item["key"] for item in body["components"]} == {
        "evidence_quality",
        "source_diversity",
        "corroboration",
        "freshness",
        "human_validation",
        "completeness",
    }
    assert body["recommended_actions"]


def test_conflicts_reduce_corroboration_and_are_disclosed(client):
    headers = auth_headers(client, email="rti-conflict@example.com")
    project = create_project(client, headers, "Conflict project")
    create_evidence(client, headers, project["id"], 10, "supports", "shared-claim")
    create_evidence(client, headers, project["id"], 11, "contradicts", "shared-claim")

    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conflict_count"] == 1
    assert body["contradicting_count"] == 1
    assert any("conflict" in limitation.lower() for limitation in body["limitations"])


def test_project_rti_is_owner_isolated(client):
    owner_headers = auth_headers(client, email="rti-owner@example.com")
    project = create_project(client, owner_headers, "Private RTI")
    create_evidence(client, owner_headers, project["id"], 20)

    other_headers = auth_headers(client, email="rti-other@example.com")
    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404
