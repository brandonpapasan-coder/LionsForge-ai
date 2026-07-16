import hashlib
import json

from tests.conftest import auth_headers


def create_project(client, headers, title="Audit project"):
    response = client.post("/api/v1/research-projects", headers=headers, json={"title": title, "objective": "Review evidence history"})
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, *, title, claim, stance="supports", key=None, provenance=None, source_url=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={"project_id": project_id, "source_url": source_url, "source_title": title, "source_type": "secondary", "claim": claim, "excerpt": f"Excerpt for {claim}", "stance": stance, "contradiction_key": key, "provenance": provenance or {}},
    )
    assert response.status_code == 201
    return response.json()


def packet_digest(packet):
    stable = {"schema_version": packet["schema_version"], "project": packet["project"], "summary": packet["summary"], "entries": packet["entries"], "disclaimer": packet["disclaimer"]}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def export_packet(client, headers, project_id):
    response = client.get(f"/api/v1/research-evidence-audit/projects/{project_id}/audit-packet", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_audit_packet_exports_project_evidence_and_integrity_hash(client):
    headers = auth_headers(client, email="audit-packet@example.com")
    project = create_project(client, headers)
    first = create_evidence(client, headers, project["id"], title="Initial source", claim="Initial claim", key="shared-question", source_url="https://example.com/initial")
    reviewed = client.patch(f"/api/v1/evidence-intelligence/{first['id']}/review", headers=headers, json={"validation_status": "needs_review", "reviewer_notes": "Compare the conflicting evidence."})
    assert reviewed.status_code == 200
    create_evidence(client, headers, project["id"], title="Revised source", claim="Revised claim", stance="contradicts", key="shared-question", provenance={"supersedes_evidence_id": first["id"]})
    body = export_packet(client, headers, project["id"])
    assert body["schema_version"] == "1.0"
    assert body["project"]["id"] == project["id"]
    assert body["summary"] == {"total_evidence": 2, "total_events": 4, "unresolved_contradictions": 1, "superseded_claims": 1, "missing_source_metadata": 1}
    assert [entry["event_type"] for entry in body["entries"]] == ["evidence_created", "review_recorded", "evidence_created", "claim_superseded"]
    assert len(body["content_sha256"]) == 64
    assert "does not certify" in body["disclaimer"]


def test_audit_packet_is_project_and_owner_scoped(client):
    owner_headers = auth_headers(client, email="audit-owner@example.com")
    other_headers = auth_headers(client, email="audit-other@example.com")
    project = create_project(client, owner_headers)
    other_project = create_project(client, owner_headers, title="Other project")
    create_evidence(client, owner_headers, project["id"], title="Included", claim="Included claim", source_url="https://example.com/included")
    create_evidence(client, owner_headers, other_project["id"], title="Excluded", claim="Excluded claim", source_url="https://example.com/excluded")
    packet = export_packet(client, owner_headers, project["id"])
    hidden = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/audit-packet", headers=other_headers)
    assert packet["summary"]["total_evidence"] == 1
    assert packet["entries"][0]["claim"] == "Included claim"
    assert hidden.status_code == 404


def test_audit_packet_verifier_accepts_an_unchanged_export(client):
    headers = auth_headers(client, email="audit-verify-valid@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="Source", claim="Reviewed claim", source_url="https://example.com/source")
    packet = export_packet(client, headers, project["id"])
    body = client.post("/api/v1/research-evidence-audit/audit-packet/verify", headers=headers, json=packet).json()
    assert body["valid"] is True
    assert body["integrity_matches"] is True
    assert body["chronology_valid"] is True
    assert body["supersession_references_valid"] is True
    assert "does not certify" in body["disclaimer"]


def test_audit_packet_verifier_detects_changed_content(client):
    headers = auth_headers(client, email="audit-verify-tampered@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="Source", claim="Original claim", source_url="https://example.com/source")
    packet = export_packet(client, headers, project["id"])
    packet["entries"][0]["claim"] = "Changed claim"
    body = client.post("/api/v1/research-evidence-audit/audit-packet/verify", headers=headers, json=packet).json()
    assert body["valid"] is False
    assert body["integrity_matches"] is False


def test_audit_packet_verifier_detects_order_and_broken_supersession(client):
    headers = auth_headers(client, email="audit-verify-structure@example.com")
    project = create_project(client, headers)
    first = create_evidence(client, headers, project["id"], title="First", claim="First claim", source_url="https://example.com/first")
    create_evidence(client, headers, project["id"], title="Second", claim="Second claim", provenance={"supersedes_evidence_id": first["id"]}, source_url="https://example.com/second")
    packet = export_packet(client, headers, project["id"])
    packet["entries"] = list(reversed(packet["entries"]))
    next(entry for entry in packet["entries"] if entry["event_type"] == "claim_superseded")["supersedes_evidence_id"] = 999999
    packet["content_sha256"] = packet_digest(packet)
    body = client.post("/api/v1/research-evidence-audit/audit-packet/verify", headers=headers, json=packet).json()
    assert body["integrity_matches"] is True
    assert body["chronology_valid"] is False
    assert body["supersession_references_valid"] is False
    assert body["valid"] is False


def test_audit_packet_comparison_classifies_added_and_unchanged_events(client):
    headers = auth_headers(client, email="audit-compare@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="First", claim="Stable claim", source_url="https://example.com/first")
    baseline = export_packet(client, headers, project["id"])
    create_evidence(client, headers, project["id"], title="Second", claim="New claim", source_url="https://example.com/second")
    current = export_packet(client, headers, project["id"])
    response = client.post("/api/v1/research-evidence-audit/audit-packet/compare", headers=headers, json={"baseline": baseline, "current": current})
    assert response.status_code == 200
    body = response.json()
    assert body["comparable"] is True
    assert body["summary"]["added"] == 1
    assert body["summary"]["unchanged"] == 1
    assert body["summary"]["summary_changed"] is True
    assert [change["classification"] for change in body["changes"]] == ["unchanged", "added"]
    assert "does not certify" in body["disclaimer"]


def test_audit_packet_comparison_reports_changed_and_removed_events(client):
    headers = auth_headers(client, email="audit-compare-changes@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="First", claim="Original claim", source_url="https://example.com/first")
    create_evidence(client, headers, project["id"], title="Second", claim="Removed claim", source_url="https://example.com/second")
    baseline = export_packet(client, headers, project["id"])
    current = json.loads(json.dumps(baseline))
    current["entries"][0]["claim"] = "Updated claim"
    current["entries"] = current["entries"][:1]
    current["summary"]["total_evidence"] = 1
    current["summary"]["total_events"] = 1
    current["content_sha256"] = packet_digest(current)
    body = client.post("/api/v1/research-evidence-audit/audit-packet/compare", headers=headers, json={"baseline": baseline, "current": current}).json()
    assert body["comparable"] is True
    assert body["summary"]["changed"] == 1
    assert body["summary"]["removed"] == 1
    changed = next(change for change in body["changes"] if change["classification"] == "changed")
    assert changed["changed_fields"] == ["claim"]


def test_audit_packet_comparison_marks_tampered_packet_not_comparable(client):
    headers = auth_headers(client, email="audit-compare-invalid@example.com")
    project = create_project(client, headers)
    create_evidence(client, headers, project["id"], title="Source", claim="Claim", source_url="https://example.com/source")
    baseline = export_packet(client, headers, project["id"])
    current = json.loads(json.dumps(baseline))
    current["entries"][0]["claim"] = "Tampered"
    body = client.post("/api/v1/research-evidence-audit/audit-packet/compare", headers=headers, json={"baseline": baseline, "current": current}).json()
    assert body["comparable"] is False
    assert body["baseline_verification"]["valid"] is True
    assert body["current_verification"]["valid"] is False


def test_audit_packet_comparison_requires_authentication(client):
    response = client.post("/api/v1/research-evidence-audit/audit-packet/compare", json={})
    assert response.status_code == 401
