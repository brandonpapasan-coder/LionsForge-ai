from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project


ENDPOINT = "/api/v1/research-conclusion-export/projects/{project_id}"
CONCLUSION_ENDPOINT = "/api/v1/research-conclusions/projects/{project_id}"


def get_packet(client, headers, project_id):
    response = client.get(ENDPOINT.format(project_id=project_id), headers=headers)
    assert response.status_code == 200
    return response.json()


def test_export_packet_represents_missing_conclusion_and_is_deterministic(client):
    headers = auth_headers(client, email="packet-empty@example.com")
    project = create_project(client, headers, title="Empty conclusion packet")

    first = get_packet(client, headers, project["id"])
    second = get_packet(client, headers, project["id"])

    assert first["content_sha256"] == second["content_sha256"]
    assert first["generated_at"] != second["generated_at"]
    assert first["content"]["conclusion_status"] == "missing"
    assert first["content"]["conclusion_text"] == ""
    assert first["content"]["evidence"] == []
    assert first["content"]["revisions"] == []
    assert first["content"]["readiness"]["state"] == "blocked"


def test_export_packet_preserves_cited_evidence_revisions_and_readiness(client):
    headers = auth_headers(client, email="packet-complete@example.com")
    project = create_project(client, headers, title="Traceable conclusion packet")
    evidence = create_evidence(
        client,
        headers,
        project["id"],
        title="Packet primary source",
        claim="Packet-supported claim",
        source_url="https://example.com/packet-source",
    )
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Reviewed for packet export."},
    )
    assert reviewed.status_code == 200

    created = client.put(
        CONCLUSION_ENDPOINT.format(project_id=project["id"]),
        headers=headers,
        json={
            "conclusion_text": "The owner authored this conclusion.",
            "evidence_ids": [evidence["id"]],
            "revision_note": "Initial packet draft.",
        },
    )
    assert created.status_code == 200

    packet = get_packet(client, headers, project["id"])
    content = packet["content"]
    assert content["conclusion_status"] == "draft"
    assert content["conclusion_text"] == "The owner authored this conclusion."
    assert content["evidence_ids"] == [evidence["id"]]
    assert content["evidence"][0]["id"] == evidence["id"]
    assert content["evidence"][0]["validation_status"] == "approved"
    assert content["evidence"][0]["reviewer_notes"] == "Reviewed for packet export."
    assert content["revisions"][0]["revision_number"] == 1
    assert content["readiness"]["state"] == "ready_for_user_conclusion"
    assert len(packet["content_sha256"]) == 64


def test_export_packet_enforces_owner_isolation(client):
    owner_headers = auth_headers(client, email="packet-owner@example.com")
    other_headers = auth_headers(client, email="packet-other@example.com")
    project = create_project(client, owner_headers, title="Private packet")

    hidden = client.get(ENDPOINT.format(project_id=project["id"]), headers=other_headers)
    assert hidden.status_code == 404

    unauthenticated = client.get(ENDPOINT.format(project_id=project["id"]))
    assert unauthenticated.status_code == 401
