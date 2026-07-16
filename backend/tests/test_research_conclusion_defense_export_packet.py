from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project


ENDPOINT = "/api/v1/research-conclusion-defense-export/projects/{project_id}"
CONCLUSION_ENDPOINT = "/api/v1/research-conclusions/projects/{project_id}"
DEFENSE_ENDPOINT = "/api/v1/research-conclusion-defense/projects/{project_id}"


def get_packet(client, headers, project_id):
    response = client.get(ENDPOINT.format(project_id=project_id), headers=headers)
    assert response.status_code == 200
    return response.json()


def test_combined_packet_represents_missing_states_and_is_deterministic(client):
    headers = auth_headers(client, email="defense-packet-empty@example.com")
    project = create_project(client, headers, title="Empty defense packet")

    first = get_packet(client, headers, project["id"])
    second = get_packet(client, headers, project["id"])

    assert first["content_sha256"] == second["content_sha256"]
    assert first["generated_at"] != second["generated_at"]
    assert first["content"]["conclusion"]["conclusion_status"] == "missing"
    assert first["content"]["defense"]["status"] == "missing"
    assert first["content"]["defense"]["revisions"] == []


def test_combined_packet_preserves_conclusion_and_defense_history(client):
    headers = auth_headers(client, email="defense-packet-complete@example.com")
    project = create_project(client, headers, title="Traceable defense packet")
    evidence = create_evidence(
        client,
        headers,
        project["id"],
        title="Defense packet source",
        claim="Evidence supports the user-authored conclusion",
        source_url="https://example.com/defense-packet",
    )
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Reviewed for combined export."},
    )
    assert reviewed.status_code == 200

    conclusion = client.put(
        CONCLUSION_ENDPOINT.format(project_id=project["id"]),
        headers=headers,
        json={
            "conclusion_text": "The owner authored this conclusion.",
            "evidence_ids": [evidence["id"]],
            "revision_note": "Initial conclusion revision.",
        },
    )
    assert conclusion.status_code == 200

    defense_payload = {
        "conclusion_revision_number": 1,
        "evidence_ids": [evidence["id"]],
        "evidence_coverage": "The cited source supports the central claim.",
        "strongest_counterargument": "The source may not generalize beyond its setting.",
        "known_limitations": "Only one directly relevant source is cited.",
        "unresolved_questions": "Would newer evidence change the conclusion?",
        "confidence_rationale": "Confidence is moderate because the evidence is relevant but narrow.",
        "revision_note": "Completed defense review.",
    }
    defense = client.put(
        DEFENSE_ENDPOINT.format(project_id=project["id"]), headers=headers, json=defense_payload
    )
    assert defense.status_code == 200

    packet = get_packet(client, headers, project["id"])
    content = packet["content"]
    assert content["conclusion"]["conclusion_text"] == "The owner authored this conclusion."
    assert content["defense"]["status"] == "complete"
    assert content["defense"]["conclusion_revision_number"] == 1
    assert content["defense"]["evidence_ids"] == [evidence["id"]]
    assert content["defense"]["revision_count"] == 1
    assert content["defense"]["revisions"][0]["revision_number"] == 1
    assert len(packet["content_sha256"]) == 64


def test_combined_packet_enforces_owner_isolation(client):
    owner_headers = auth_headers(client, email="defense-packet-owner@example.com")
    other_headers = auth_headers(client, email="defense-packet-other@example.com")
    project = create_project(client, owner_headers, title="Private defense packet")

    hidden = client.get(ENDPOINT.format(project_id=project["id"]), headers=other_headers)
    assert hidden.status_code == 404

    unauthenticated = client.get(ENDPOINT.format(project_id=project["id"]))
    assert unauthenticated.status_code == 401
