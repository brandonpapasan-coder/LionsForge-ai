from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project


ENDPOINT = "/api/v1/research-conclusions/projects/{project_id}"


def test_conclusion_workspace_starts_empty_and_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="conclusion-owner@example.com")
    other_headers = auth_headers(client, email="conclusion-other@example.com")
    project = create_project(client, owner_headers, title="Private conclusion project")

    empty = client.get(ENDPOINT.format(project_id=project["id"]), headers=owner_headers)
    assert empty.status_code == 200
    assert empty.json()["id"] is None
    assert empty.json()["status"] == "draft"
    assert empty.json()["revision_count"] == 0

    hidden = client.get(ENDPOINT.format(project_id=project["id"]), headers=other_headers)
    assert hidden.status_code == 404
    unauthenticated = client.get(ENDPOINT.format(project_id=project["id"]))
    assert unauthenticated.status_code == 401


def test_conclusion_workspace_creates_revisions_and_deduplicates_evidence(client):
    headers = auth_headers(client, email="conclusion-revisions@example.com")
    project = create_project(client, headers, title="Conclusion revision project")
    first = create_evidence(
        client,
        headers,
        project["id"],
        title="First conclusion source",
        claim="First supported claim",
        source_url="https://example.com/conclusion-first",
    )

    created = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=headers,
        json={
            "conclusion_text": "The project owner authored this initial conclusion.",
            "evidence_ids": [first["id"], first["id"]],
            "revision_note": "Initial draft.",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "draft"
    assert body["evidence_ids"] == [first["id"]]
    assert body["revision_count"] == 1
    assert body["revisions"][0]["revision_number"] == 1

    revised = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=headers,
        json={
            "conclusion_text": "The project owner revised the conclusion after review.",
            "evidence_ids": [first["id"]],
            "revision_note": "Clarified scope.",
        },
    )
    assert revised.status_code == 200
    revised_body = revised.json()
    assert revised_body["status"] == "revised"
    assert revised_body["revision_count"] == 2
    assert [item["revision_number"] for item in revised_body["revisions"]] == [2, 1]

    unchanged = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=headers,
        json={
            "conclusion_text": "The project owner revised the conclusion after review.",
            "evidence_ids": [first["id"]],
        },
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["revision_count"] == 2


def test_conclusion_workspace_rejects_foreign_evidence_and_requires_finalization_confirmation(client):
    owner_headers = auth_headers(client, email="conclusion-finalize@example.com")
    other_headers = auth_headers(client, email="conclusion-evidence-other@example.com")
    project = create_project(client, owner_headers, title="Final conclusion project")
    other_project = create_project(client, other_headers, title="Other evidence project")
    evidence = create_evidence(
        client,
        other_headers,
        other_project["id"],
        title="Foreign source",
        claim="Foreign claim",
        source_url="https://example.com/foreign-conclusion",
    )

    invalid = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=owner_headers,
        json={"conclusion_text": "Owner text.", "evidence_ids": [evidence["id"]]},
    )
    assert invalid.status_code == 422

    unconfirmed = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=owner_headers,
        json={"conclusion_text": "Final owner-authored conclusion.", "finalize": True},
    )
    assert unconfirmed.status_code == 400

    finalized = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=owner_headers,
        json={
            "conclusion_text": "Final owner-authored conclusion.",
            "evidence_ids": [],
            "revision_note": "Owner confirmed finalization.",
            "finalize": True,
            "confirmed": True,
        },
    )
    assert finalized.status_code == 200
    body = finalized.json()
    assert body["status"] == "finalized"
    assert body["finalized_at"] is not None
    assert body["revisions"][0]["status"] == "finalized"

    denied_revision = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=owner_headers,
        json={"conclusion_text": "A later revision needs confirmation."},
    )
    assert denied_revision.status_code == 400

    confirmed_revision = client.put(
        ENDPOINT.format(project_id=project["id"]),
        headers=owner_headers,
        json={
            "conclusion_text": "A later owner-confirmed revision.",
            "revision_note": "Reopened by owner.",
            "confirmed": True,
        },
    )
    assert confirmed_revision.status_code == 200
    assert confirmed_revision.json()["status"] == "revised"
    assert confirmed_revision.json()["finalized_at"] is None
