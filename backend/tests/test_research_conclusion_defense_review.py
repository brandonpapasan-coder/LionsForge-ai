from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project


ENDPOINT = "/api/v1/research-conclusion-defense/projects/{project_id}"
CONCLUSION_ENDPOINT = "/api/v1/research-conclusions/projects/{project_id}"


def test_defense_review_starts_incomplete_and_is_owner_scoped(client):
    owner = auth_headers(client, email="defense-owner@example.com")
    other = auth_headers(client, email="defense-other@example.com")
    project = create_project(client, owner, title="Defense project")

    response = client.get(ENDPOINT.format(project_id=project["id"]), headers=owner)
    assert response.status_code == 200
    assert response.json()["status"] == "incomplete"
    assert len(response.json()["missing_sections"]) == 5
    assert client.get(ENDPOINT.format(project_id=project["id"]), headers=other).status_code == 404


def test_defense_review_tracks_completeness_and_immutable_revisions(client):
    headers = auth_headers(client, email="defense-revisions@example.com")
    project = create_project(client, headers, title="Defense revision project")
    evidence = create_evidence(client, headers, project["id"], title="Defense source", claim="Supported claim", source_url="https://example.com/defense")
    conclusion = client.put(CONCLUSION_ENDPOINT.format(project_id=project["id"]), headers=headers, json={"conclusion_text": "Owner conclusion", "evidence_ids": [evidence["id"]], "revision_note": "Initial"})
    assert conclusion.status_code == 200

    incomplete = client.put(ENDPOINT.format(project_id=project["id"]), headers=headers, json={"evidence_coverage": "Coverage notes", "evidence_ids": [evidence["id"]], "conclusion_revision_number": 1})
    assert incomplete.status_code == 200
    assert incomplete.json()["status"] == "incomplete"
    assert incomplete.json()["revision_count"] == 1

    complete_payload = {
        "evidence_coverage": "Coverage notes",
        "strongest_counterargument": "A serious counterargument",
        "known_limitations": "Known limits",
        "unresolved_questions": "Open questions",
        "confidence_rationale": "Confidence is provisional",
        "evidence_ids": [evidence["id"], evidence["id"]],
        "conclusion_revision_number": 1,
        "revision_note": "Completed reflection",
    }
    complete = client.put(ENDPOINT.format(project_id=project["id"]), headers=headers, json=complete_payload)
    assert complete.status_code == 200
    body = complete.json()
    assert body["status"] == "complete"
    assert body["missing_sections"] == []
    assert body["evidence_ids"] == [evidence["id"]]
    assert body["revision_count"] == 2
    assert [item["revision_number"] for item in body["revisions"]] == [2, 1]

    unchanged = client.put(ENDPOINT.format(project_id=project["id"]), headers=headers, json=complete_payload)
    assert unchanged.status_code == 200
    assert unchanged.json()["revision_count"] == 2


def test_defense_review_rejects_foreign_links(client):
    owner = auth_headers(client, email="defense-link-owner@example.com")
    other = auth_headers(client, email="defense-link-other@example.com")
    project = create_project(client, owner, title="Owner project")
    other_project = create_project(client, other, title="Other project")
    foreign = create_evidence(client, other, other_project["id"], title="Foreign source", claim="Foreign claim", source_url="https://example.com/foreign-defense")

    invalid_evidence = client.put(ENDPOINT.format(project_id=project["id"]), headers=owner, json={"evidence_ids": [foreign["id"]]})
    assert invalid_evidence.status_code == 422

    invalid_revision = client.put(ENDPOINT.format(project_id=project["id"]), headers=owner, json={"conclusion_revision_number": 99})
    assert invalid_revision.status_code == 422
