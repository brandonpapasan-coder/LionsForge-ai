from tests.conftest import auth_headers


def create_project(client, headers, title="Executive governance"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Produce an executive governance summary"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index, stance="supports", key=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://executive-source{index}.example.com/report",
            "source_title": f"Executive source {index}",
            "publisher": f"Publisher {index}",
            "author": f"Analyst {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "official",
            "claim": f"Governance finding {index}",
            "excerpt": f"Documented result {index}",
            "stance": stance,
            "contradiction_key": key,
            "provenance": {"test_source": index},
        },
    )
    assert response.status_code == 201
    return response.json()


def review_evidence(client, headers, evidence_id, status, notes):
    response = client.patch(
        f"/api/v1/evidence-intelligence/{evidence_id}/review",
        headers=headers,
        json={"validation_status": status, "reviewer_notes": notes},
    )
    assert response.status_code == 200


def snapshot(client, headers, project_id):
    response = client.get(
        f"/api/v1/research-trust-index/projects/{project_id}/governance-snapshot",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_governance_snapshot_includes_deterministic_executive_summary(client):
    headers = auth_headers(client, email="executive-summary@example.com")
    project = create_project(client, headers)
    first = create_evidence(client, headers, project["id"], 1)
    create_evidence(client, headers, project["id"], 2)
    review_evidence(client, headers, first["id"], "approved", "Validated")

    body = snapshot(client, headers, project["id"])
    summary = body["executive_summary"]

    assert summary["trust_status"] in {"strong", "moderate", "weak"}
    assert summary["risk_level"] in {"controlled", "elevated", "high"}
    assert summary["evidence_review_rate"] == 0.5
    assert summary["approval_rate"] == 0.5
    assert "1 of 2 evidence records" in summary["headline"]
    assert summary["key_strengths"] == body["trust_index"]["strengths"][:3]
    assert summary["key_risks"] == body["trust_index"]["limitations"][:3]
    assert summary["priority_actions"] == body["trust_index"]["recommended_actions"][:5]


def test_conflicts_raise_executive_governance_risk(client):
    headers = auth_headers(client, email="executive-risk@example.com")
    project = create_project(client, headers, "Conflict governance")
    create_evidence(client, headers, project["id"], 10, "supports", "shared-outcome")
    create_evidence(client, headers, project["id"], 11, "contradicts", "shared-outcome")

    body = snapshot(client, headers, project["id"])

    assert body["trust_index"]["conflict_count"] == 1
    assert body["executive_summary"]["risk_level"] == "high"
    assert "high governance risk" in body["executive_summary"]["headline"]


def test_empty_project_summary_uses_zero_rates_without_division_errors(client):
    headers = auth_headers(client, email="executive-empty@example.com")
    project = create_project(client, headers, "Empty governance")

    body = snapshot(client, headers, project["id"])

    assert body["trust_index"]["evidence_count"] == 0
    assert body["executive_summary"]["evidence_review_rate"] == 0
    assert body["executive_summary"]["approval_rate"] == 0
