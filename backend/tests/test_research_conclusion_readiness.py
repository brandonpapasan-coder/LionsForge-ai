from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project
from tests.test_research_review_actions_api import build_changed_packets


ENDPOINT = "/api/v1/research-conclusion-readiness/projects/{project_id}"


def get_readiness(client, headers, project_id):
    response = client.get(ENDPOINT.format(project_id=project_id), headers=headers)
    assert response.status_code == 200
    return response.json()


def test_readiness_blocks_projects_without_evidence_and_is_deterministic(client):
    headers = auth_headers(client, email="readiness-empty@example.com")
    project = create_project(client, headers, title="Empty readiness project")

    first = get_readiness(client, headers, project["id"])
    second = get_readiness(client, headers, project["id"])

    assert first == second
    assert first["state"] == "blocked"
    assert first["blocking_count"] == 1
    assert first["evidence_count"] == 0
    assert first["checks"][0]["code"] == "evidence_present"
    assert first["checks"][0]["passed"] is False


def test_readiness_reports_needs_review_then_ready_after_evidence_review(client):
    headers = auth_headers(client, email="readiness-review@example.com")
    project = create_project(client, headers, title="Evidence readiness project")
    evidence = create_evidence(
        client,
        headers,
        project["id"],
        title="Readiness evidence",
        claim="A traceable claim",
        source_url="https://example.com/readiness",
    )

    needs_review = get_readiness(client, headers, project["id"])
    assert needs_review["state"] == "needs_review"
    assert needs_review["blocking_count"] == 0
    assert needs_review["caution_count"] == 1
    evidence_check = next(item for item in needs_review["checks"] if item["code"] == "evidence_reviewed")
    assert evidence_check["evidence_ids"] == [evidence["id"]]

    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Source and claim were reviewed."},
    )
    assert reviewed.status_code == 200

    ready = get_readiness(client, headers, project["id"])
    assert ready["state"] == "ready_for_user_conclusion"
    assert ready["blocking_count"] == 0
    assert ready["caution_count"] == 0
    assert all(item["passed"] for item in ready["checks"])


def test_readiness_blocks_active_high_attention_actions_with_traceability(client):
    headers = auth_headers(client, email="readiness-action@example.com")
    project, baseline, current = build_changed_packets(client, headers)
    generated = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=headers,
        json={"baseline": baseline, "current": current},
    )
    assert generated.status_code == 200
    actions = generated.json()["actions"]
    assert actions

    readiness = get_readiness(client, headers, project["id"])
    high_attention = [item for item in actions if item["impact_level"] == "high_attention"]
    if high_attention:
        assert readiness["state"] == "blocked"
        check = next(item for item in readiness["checks"] if item["code"] == "high_attention_actions_cleared")
        assert check["passed"] is False
        assert check["action_ids"] == [item["id"] for item in high_attention]
        assert check["governing_rules"]
        assert check["event_ids"]
    else:
        assert readiness["state"] == "needs_review"
        check = next(item for item in readiness["checks"] if item["code"] == "review_required_actions_cleared")
        assert check["passed"] is False
        assert check["action_ids"]


def test_readiness_enforces_owner_isolation(client):
    owner_headers = auth_headers(client, email="readiness-owner@example.com")
    other_headers = auth_headers(client, email="readiness-other@example.com")
    project = create_project(client, owner_headers, title="Private readiness project")

    hidden = client.get(ENDPOINT.format(project_id=project["id"]), headers=other_headers)
    assert hidden.status_code == 404

    unauthenticated = client.get(ENDPOINT.format(project_id=project["id"]))
    assert unauthenticated.status_code == 401
