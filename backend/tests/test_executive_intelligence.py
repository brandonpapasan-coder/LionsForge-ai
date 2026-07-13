from tests.conftest import auth_headers


def create_project(client, headers, title="Executive brief project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Make an evidence-backed decision"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index, stance="supports", key=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://executive{index}.example.com/report",
            "source_title": f"Executive report {index}",
            "publisher": f"Executive Institute {index}",
            "author": f"Analyst {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": f"Executive finding {index}",
            "excerpt": f"Documented executive evidence {index}",
            "stance": stance,
            "contradiction_key": key,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_executive_brief_is_traceable_and_deterministic(client):
    headers = auth_headers(client, email="executive@example.com")
    project = create_project(client, headers)
    evidence = [
        create_evidence(client, headers, project["id"], index)
        for index in range(1, 5)
    ]

    url = f"/api/v1/executive-intelligence/projects/{project['id']}"
    first = client.get(url, headers=headers)
    second = client.get(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    body = first.json()
    assert body == second.json()
    assert body["methodology_version"] == "executive-brief-v1"
    assert body["project_id"] == project["id"]
    assert body["source_evidence_ids"] == sorted(item["id"] for item in evidence)
    assert body["recommendation"] in {
        "go",
        "hold",
        "investigate",
        "insufficient_evidence",
    }
    assert 0 <= body["decision_readiness_score"] <= 100
    assert body["executive_summary"]


def test_executive_brief_preserves_conflicts_and_minority_findings(client):
    headers = auth_headers(client, email="executive-conflict@example.com")
    project = create_project(client, headers, "Conflicted executive brief")
    create_evidence(client, headers, project["id"], 10, "supports", "outcome")
    contradiction = create_evidence(
        client,
        headers,
        project["id"],
        11,
        "contradicts",
        "outcome",
    )

    response = client.get(
        f"/api/v1/executive-intelligence/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "investigate"
    assert body["risks"]
    assert contradiction["claim"] in body["minority_findings"]
    assert contradiction["id"] in body["source_evidence_ids"]
    assert body["unresolved_questions"]


def test_executive_brief_reports_insufficient_evidence(client):
    headers = auth_headers(client, email="executive-empty@example.com")
    project = create_project(client, headers, "Empty executive brief")

    response = client.get(
        f"/api/v1/executive-intelligence/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "insufficient_evidence"
    assert body["source_evidence_ids"] == []
    assert body["decision_readiness_score"] == 30.0


def test_executive_brief_requires_owned_project(client):
    owner_headers = auth_headers(client, email="executive-owner@example.com")
    project = create_project(client, owner_headers, "Private executive brief")
    create_evidence(client, owner_headers, project["id"], 20)

    other_headers = auth_headers(client, email="executive-other@example.com")
    response = client.get(
        f"/api/v1/executive-intelligence/projects/{project['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404
