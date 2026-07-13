from tests.conftest import auth_headers


def create_project(client, headers, title="Consensus project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Reach an evidence-backed consensus"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index, stance="supports", key=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://consensus{index}.example.com/report",
            "source_title": f"Consensus report {index}",
            "publisher": f"Consensus Institute {index}",
            "author": f"Analyst {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": f"Consensus finding {index}",
            "excerpt": f"Documented evidence excerpt {index}",
            "stance": stance,
            "contradiction_key": key,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_consensus_returns_specialist_findings_and_rti(client):
    headers = auth_headers(client, email="consensus@example.com")
    project = create_project(client, headers)
    for index in range(1, 6):
        create_evidence(client, headers, project["id"], index, key="outcome")

    response = client.get(
        f"/api/v1/multi-agent-consensus/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["methodology_version"] == "consensus-v1"
    assert body["research_trust_index"] >= 0
    assert {item["agent"] for item in body["findings"]} == {
        "research",
        "evidence",
        "verification",
    }
    assert body["consensus_status"] in {
        "strong_agreement",
        "moderate_agreement",
        "split",
    }


def test_consensus_preserves_conflicts_and_reduces_certainty(client):
    headers = auth_headers(client, email="consensus-conflict@example.com")
    project = create_project(client, headers, "Conflict consensus")
    create_evidence(client, headers, project["id"], 10, "supports", "shared-claim")
    create_evidence(client, headers, project["id"], 11, "contradicts", "shared-claim")

    response = client.get(
        f"/api/v1/multi-agent-consensus/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["consensus_status"] == "split"
    assert len(body["conflicts"]) == 1
    assert body["conflicts"][0]["key"] == "shared-claim"
    assert body["unresolved_questions"]


def test_consensus_requires_owned_project(client):
    owner_headers = auth_headers(client, email="consensus-owner@example.com")
    project = create_project(client, owner_headers, "Private consensus")
    create_evidence(client, owner_headers, project["id"], 20)

    other_headers = auth_headers(client, email="consensus-other@example.com")
    response = client.get(
        f"/api/v1/multi-agent-consensus/projects/{project['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404
