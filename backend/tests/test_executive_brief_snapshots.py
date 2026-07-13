from tests.conftest import auth_headers


def create_project(client, headers, title="Snapshot project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Track decision changes"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://snapshot{index}.example.com/report",
            "source_title": f"Snapshot report {index}",
            "publisher": f"Snapshot Institute {index}",
            "author": f"Analyst {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": f"Snapshot finding {index}",
            "excerpt": f"Documented snapshot evidence {index}",
            "stance": "supports",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_snapshot_creation_reuses_identical_state_and_preserves_payload(client):
    headers = auth_headers(client, email="snapshot@example.com")
    project = create_project(client, headers)
    evidence = create_evidence(client, headers, project["id"], 1)
    url = f"/api/v1/executive-intelligence/projects/{project['id']}/snapshots"

    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["snapshot"]["id"] == second.json()["snapshot"]["id"]
    assert first.json()["snapshot"]["source_evidence_ids"] == [evidence["id"]]
    assert first.json()["snapshot"]["payload"]["methodology_version"] == "executive-brief-v1"


def test_snapshot_history_and_comparison_track_evidence_change(client):
    headers = auth_headers(client, email="snapshot-history@example.com")
    project = create_project(client, headers, "History project")
    url = f"/api/v1/executive-intelligence/projects/{project['id']}/snapshots"

    create_evidence(client, headers, project["id"], 10)
    left = client.post(url, headers=headers).json()["snapshot"]
    added = create_evidence(client, headers, project["id"], 11)
    right = client.post(url, headers=headers).json()["snapshot"]

    history = client.get(url, headers=headers)
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [right["id"], left["id"]]

    comparison = client.get(
        f"/api/v1/executive-intelligence/snapshots/{left['id']}/compare/{right['id']}",
        headers=headers,
    )
    assert comparison.status_code == 200
    assert comparison.json()["evidence_added"] == [added["id"]]
    assert comparison.json()["evidence_removed"] == []


def test_snapshot_access_is_owner_isolated(client):
    owner_headers = auth_headers(client, email="snapshot-owner@example.com")
    project = create_project(client, owner_headers, "Private snapshot")
    snapshot = client.post(
        f"/api/v1/executive-intelligence/projects/{project['id']}/snapshots",
        headers=owner_headers,
    ).json()["snapshot"]

    other_headers = auth_headers(client, email="snapshot-other@example.com")
    assert client.get(
        f"/api/v1/executive-intelligence/snapshots/{snapshot['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/executive-intelligence/projects/{project['id']}/snapshots",
        headers=other_headers,
    ).status_code == 404
