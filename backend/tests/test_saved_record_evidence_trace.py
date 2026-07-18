from tests.conftest import auth_headers


def create_project(client, headers, title):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Trace saved record evidence"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, *, source_url="https://example.com/source"):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": source_url,
            "source_title": "Primary source",
            "publisher": "Example Institute",
            "author": "A. Researcher",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": "The intervention improved measured outcomes.",
            "excerpt": "Measured outcomes improved during the controlled evaluation.",
            "stance": "supports",
            "contradiction_key": None,
            "provenance": {"ingestion_method": "manual"},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_memory(client, headers, project_id, evidence_ids):
    response = client.post(
        "/api/v1/knowledge-memory/user-authored",
        headers=headers,
        json={
            "project_id": project_id,
            "statement": "The intervention improved measured outcomes.",
            "summary": "Intervention outcome finding",
            "category": "research_context",
            "confidence": 0.8,
            "source_evidence_ids": evidence_ids,
            "provenance": {"basis": "reviewed evidence"},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_saved_record_evidence_trace_preserves_record_order_and_reports_unavailable(client):
    headers = auth_headers(client, email="memory-evidence@example.com")
    project = create_project(client, headers, "Trace project")
    first = create_evidence(client, headers, project["id"])
    second = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.org/second-source",
    )
    memory = create_memory(
        client,
        headers,
        project["id"],
        [second["id"], 999999, first["id"], second["id"]],
    )

    response = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    expected_requested = list(dict.fromkeys(memory["source_evidence_ids"]))
    assert body["memory_id"] == memory["id"]
    assert body["requested_evidence_ids"] == expected_requested
    assert [item["id"] for item in body["evidence"]] == [
        evidence_id for evidence_id in expected_requested if evidence_id != 999999
    ]
    assert body["unavailable_evidence_ids"] == [999999]
    source_by_id = {item["id"]: item for item in body["evidence"]}
    assert source_by_id[second["id"]]["source_title"] == "Primary source"
    assert source_by_id[second["id"]]["source_url"] == "https://example.org/second-source"
    assert source_by_id[second["id"]]["validation_status"] == "unverified"


def test_saved_record_evidence_trace_enforces_owner_isolation(client):
    owner_headers = auth_headers(client, email="memory-evidence-owner@example.com")
    other_headers = auth_headers(client, email="memory-evidence-other@example.com")
    owner_project = create_project(client, owner_headers, "Owner trace project")
    other_project = create_project(client, other_headers, "Other trace project")
    owner_evidence = create_evidence(client, owner_headers, owner_project["id"])
    other_evidence = create_evidence(
        client,
        other_headers,
        other_project["id"],
        source_url="https://example.net/private-source",
    )
    memory = create_memory(
        client,
        owner_headers,
        owner_project["id"],
        [owner_evidence["id"], other_evidence["id"]],
    )

    trace = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence",
        headers=owner_headers,
    )
    assert trace.status_code == 200
    assert [item["id"] for item in trace.json()["evidence"]] == [owner_evidence["id"]]
    assert trace.json()["unavailable_evidence_ids"] == [other_evidence["id"]]

    denied = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence",
        headers=other_headers,
    )
    assert denied.status_code == 404
