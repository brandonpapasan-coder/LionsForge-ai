from tests.conftest import auth_headers


def create_project(client, headers, title="Governance project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Review evidence governance"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(
    client,
    headers,
    project_id,
    *,
    title,
    claim,
    provenance=None,
    source_url=None,
):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": source_url,
            "source_title": title,
            "source_type": "secondary",
            "claim": claim,
            "excerpt": f"Excerpt for {claim}",
            "stance": "supports",
            "provenance": provenance or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def export_packet(client, headers, project_id):
    response = client.get(
        f"/api/v1/research-evidence-audit/projects/{project_id}/audit-packet",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_governance_dashboard_returns_deterministic_empty_state(client):
    headers = auth_headers(client, email="governance-empty@example.com")
    project = create_project(client, headers, title="Empty governance project")
    first = client.get(
        f"/api/v1/research-governance-dashboard/projects/{project['id']}?days=30",
        headers=headers,
    )
    second = client.get(
        f"/api/v1/research-governance-dashboard/projects/{project['id']}?days=30",
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["total_actions"] == 0
    assert first.json()["status_metrics"] == second.json()["status_metrics"]
    assert first.json()["trace_items"] == []


def test_governance_dashboard_aggregates_actions_and_traceability(client):
    headers = auth_headers(client, email="governance-actions@example.com")
    project = create_project(client, headers, title="Governance project")
    first = create_evidence(
        client,
        headers,
        project["id"],
        title="Initial",
        claim="Initial claim",
        source_url="https://example.com/initial",
    )
    baseline = export_packet(client, headers, project["id"])
    create_evidence(
        client,
        headers,
        project["id"],
        title="Replacement",
        claim="Replacement claim",
        provenance={"supersedes_evidence_id": first["id"]},
        source_url="https://example.com/replacement",
    )
    current = export_packet(client, headers, project["id"])
    generated = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=headers,
        json={"baseline": baseline, "current": current},
    )
    assert generated.status_code == 200
    action = generated.json()["actions"][0]
    resolved = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=headers,
        json={"status": "resolved", "confirmed": True, "note": "Reviewed"},
    )
    assert resolved.status_code == 200
    reopened = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=headers,
        json={"status": "open", "confirmed": True, "note": "New evidence"},
    )
    assert reopened.status_code == 200

    body = client.get(
        f"/api/v1/research-governance-dashboard/projects/{project['id']}?days=30",
        headers=headers,
    ).json()
    assert body["total_actions"] >= 1
    assert body["throughput"]["resolved_transitions"] == 1
    assert body["throughput"]["reopened_transitions"] == 1
    trace = next(item for item in body["trace_items"] if item["action_id"] == action["id"])
    assert trace["reopen_count"] == 1
    assert trace["supporting_event_ids"]
    assert trace["governing_rule"]


def test_governance_dashboard_enforces_owner_and_authentication(client):
    owner = auth_headers(client, email="governance-owner@example.com")
    other = auth_headers(client, email="governance-other@example.com")
    project = create_project(client, owner, title="Private governance project")
    hidden = client.get(
        f"/api/v1/research-governance-dashboard/projects/{project['id']}",
        headers=other,
    )
    unauthenticated = client.get(
        f"/api/v1/research-governance-dashboard/projects/{project['id']}"
    )
    assert hidden.status_code == 404
    assert unauthenticated.status_code == 401
