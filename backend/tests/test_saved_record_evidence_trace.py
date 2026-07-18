from tests.conftest import auth_headers


def create_project(client, headers, title):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Trace saved record evidence"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(
    client,
    headers,
    project_id,
    *,
    source_url="https://example.com/source",
    stance="supports",
):
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
            "stance": stance,
            "contradiction_key": "intervention-outcome" if stance == "contradicts" else None,
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


def get_trace(client, headers, memory_id):
    response = client.get(
        f"/api/v1/knowledge-memory/{memory_id}/evidence",
        headers=headers,
    )
    assert response.status_code == 200
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

    body = get_trace(client, headers, memory["id"])
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
    assert body["health"]["total_count"] == 3
    assert body["health"]["available_count"] == 2
    assert body["health"]["unavailable_count"] == 1
    assert body["health"]["supporting_count"] == 2
    assert body["health"]["needs_review_count"] == 2
    assert body["health"]["classification"] in {"adequate", "weak"}


def test_saved_record_evidence_health_is_unsupported_without_links(client):
    headers = auth_headers(client, email="memory-evidence-unsupported@example.com")
    project = create_project(client, headers, "Unsupported health project")
    memory = create_memory(client, headers, project["id"], [])

    health = get_trace(client, headers, memory["id"])["health"]

    assert health["classification"] == "unsupported"
    assert health["total_count"] == 0
    assert health["available_count"] == 0
    assert health["reasons"] == ["This saved record has no linked evidence."]
    assert health["recommended_actions"]


def test_saved_record_evidence_health_is_unavailable_when_no_links_resolve(client):
    headers = auth_headers(client, email="memory-evidence-unavailable@example.com")
    project = create_project(client, headers, "Unavailable health project")
    memory = create_memory(client, headers, project["id"], [888888, 999999])

    health = get_trace(client, headers, memory["id"])["health"]

    assert health["classification"] == "unavailable"
    assert health["total_count"] == 2
    assert health["available_count"] == 0
    assert health["unavailable_count"] == 2


def test_saved_record_evidence_health_is_contested_with_support_and_contradiction(client):
    headers = auth_headers(client, email="memory-evidence-contested@example.com")
    project = create_project(client, headers, "Contested health project")
    supporting = create_evidence(client, headers, project["id"])
    contradicting = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.org/contradiction",
        stance="contradicts",
    )
    memory = create_memory(client, headers, project["id"], [supporting["id"], contradicting["id"]])

    health = get_trace(client, headers, memory["id"])["health"]

    assert health["classification"] == "contested"
    assert health["supporting_count"] == 1
    assert health["contradicting_count"] == 1
    assert any("supporting and contradicting" in reason for reason in health["reasons"])


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

    trace = get_trace(client, owner_headers, memory["id"])
    assert [item["id"] for item in trace["evidence"]] == [owner_evidence["id"]]
    assert trace["unavailable_evidence_ids"] == [other_evidence["id"]]
    assert trace["health"]["available_count"] == 1
    assert trace["health"]["unavailable_count"] == 1

    denied = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence",
        headers=other_headers,
    )
    assert denied.status_code == 404
