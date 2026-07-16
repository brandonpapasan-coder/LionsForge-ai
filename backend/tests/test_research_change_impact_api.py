import hashlib
import json

from tests.conftest import auth_headers


def create_project(client, headers):
    response = client.post("/api/v1/research-projects", headers=headers, json={"title": "Impact project", "objective": "Assess evidence changes"})
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, *, title, claim, source_url="https://example.com/source", provenance=None, key=None):
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
            "contradiction_key": key,
            "provenance": provenance or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def digest(packet):
    stable = {key: packet[key] for key in ["schema_version", "project", "summary", "entries", "disclaimer"]}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_impact_assessment_prioritizes_removed_and_superseded_evidence(client):
    headers = auth_headers(client, email="impact@example.com")
    project = create_project(client, headers)
    first = create_evidence(client, headers, project["id"], title="Initial", claim="Initial claim")
    baseline = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/audit-packet", headers=headers).json()
    create_evidence(client, headers, project["id"], title="Replacement", claim="Replacement claim", provenance={"supersedes_evidence_id": first["id"]})
    current = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/audit-packet", headers=headers).json()

    response = client.post("/api/v1/research-evidence-audit/audit-packet/impact-assessment", headers=headers, json={"baseline": baseline, "current": current})
    assert response.status_code == 200
    body = response.json()
    assert body["comparable"] is True
    assert body["summary"]["high_attention"] >= 1
    assert body["summary"]["material_change"] is True
    assert any("supersession_changed" in item["rules"] for item in body["impacts"])
    assert "does not certify" in body["disclaimer"]


def test_impact_assessment_reports_no_material_change_for_identical_packets(client):
    headers = auth_headers(client, email="impact-unchanged@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="Stable", claim="Stable claim")
    packet = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/audit-packet", headers=headers).json()

    body = client.post("/api/v1/research-evidence-audit/audit-packet/impact-assessment", headers=headers, json={"baseline": packet, "current": packet}).json()
    assert body["summary"] == {"high_attention": 0, "review_required": 0, "informational": 0, "material_change": False}
    assert body["impacts"] == []
    assert "No material provenance changes" in body["global_actions"][0]


def test_impact_assessment_rejects_tampered_packet_from_comparison(client):
    headers = auth_headers(client, email="impact-invalid@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="Source", claim="Original")
    baseline = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/audit-packet", headers=headers).json()
    current = json.loads(json.dumps(baseline))
    current["entries"][0]["claim"] = "Tampered"
    current["content_sha256"] = "0" * 64

    body = client.post("/api/v1/research-evidence-audit/audit-packet/impact-assessment", headers=headers, json={"baseline": baseline, "current": current}).json()
    assert body["comparable"] is False
    assert body["impacts"] == []
    assert "verification failures" in body["global_actions"][0]


def test_impact_assessment_requires_authentication(client):
    packet = {
        "schema_version": "1.0",
        "generated_at": "2026-07-16T00:00:00Z",
        "project": {"id": 1, "title": "P", "description": None, "objective": None, "status": "active", "created_at": "2026-07-16T00:00:00Z", "updated_at": "2026-07-16T00:00:00Z"},
        "summary": {"total_evidence": 0, "total_events": 0, "unresolved_contradictions": 0, "superseded_claims": 0, "missing_source_metadata": 0},
        "entries": [],
        "disclaimer": "This packet records origin and review history.",
        "content_sha256": "",
    }
    packet["content_sha256"] = digest(packet)
    response = client.post("/api/v1/research-evidence-audit/audit-packet/impact-assessment", json={"baseline": packet, "current": packet})
    assert response.status_code == 401
