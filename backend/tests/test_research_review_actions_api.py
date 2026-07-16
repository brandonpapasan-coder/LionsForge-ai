from tests.conftest import auth_headers
from tests.test_research_evidence_audit_packet_api import create_evidence, create_project, export_packet


def build_changed_packets(client, headers):
    project = create_project(client, headers, title="Review action project")
    first = create_evidence(client, headers, project["id"], title="First", claim="Initial claim", source_url="https://example.com/first")
    baseline = export_packet(client, headers, project["id"])
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{first['id']}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Recheck the supporting source."},
    )
    assert reviewed.status_code == 200
    current = export_packet(client, headers, project["id"])
    return project, baseline, current


def test_review_actions_generate_deterministically_and_do_not_duplicate(client):
    headers = auth_headers(client, email="review-action-generate@example.com")
    project, baseline, current = build_changed_packets(client, headers)
    payload = {"baseline": baseline, "current": current}
    first = client.post("/api/v1/research-evidence-audit/review-actions/generate", headers=headers, json=payload)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["project_id"] == project["id"]
    assert first_body["generated"] >= 1
    assert all(item["status"] == "open" for item in first_body["actions"])
    second = client.post("/api/v1/research-evidence-audit/review-actions/generate", headers=headers, json=payload)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["generated"] == 0
    assert second_body["existing"] == len(first_body["actions"])
    assert [item["action_key"] for item in second_body["actions"]] == [item["action_key"] for item in first_body["actions"]]


def test_review_action_transition_requires_confirmation_and_records_history(client):
    headers = auth_headers(client, email="review-action-transition@example.com")
    _, baseline, current = build_changed_packets(client, headers)
    action = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=headers,
        json={"baseline": baseline, "current": current},
    ).json()["actions"][0]
    denied = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=headers,
        json={"status": "acknowledged", "confirmed": False},
    )
    assert denied.status_code == 400
    updated = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=headers,
        json={"status": "acknowledged", "confirmed": True, "note": "Assigned for review."},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["status"] == "acknowledged"
    assert body["history"][-1]["previous_status"] == "open"
    assert body["history"][-1]["new_status"] == "acknowledged"
    assert body["history"][-1]["note"] == "Assigned for review."


def test_review_action_transition_is_idempotent_and_owner_scoped(client):
    owner_headers = auth_headers(client, email="review-action-owner@example.com")
    other_headers = auth_headers(client, email="review-action-other@example.com")
    project, baseline, current = build_changed_packets(client, owner_headers)
    action = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=owner_headers,
        json={"baseline": baseline, "current": current},
    ).json()["actions"][0]
    first = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=owner_headers,
        json={"status": "resolved", "confirmed": True},
    ).json()
    second = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=owner_headers,
        json={"status": "resolved", "confirmed": True},
    ).json()
    assert len(second["history"]) == len(first["history"])
    hidden = client.get(f"/api/v1/research-evidence-audit/projects/{project['id']}/review-actions", headers=other_headers)
    assert hidden.status_code == 404
    forbidden = client.patch(
        f"/api/v1/research-evidence-audit/review-actions/{action['id']}",
        headers=other_headers,
        json={"status": "open", "confirmed": True},
    )
    assert forbidden.status_code == 404


def test_review_actions_reject_unverified_packets_and_authentication(client):
    headers = auth_headers(client, email="review-action-invalid@example.com")
    _, baseline, current = build_changed_packets(client, headers)
    current["entries"][0]["claim"] = "Tampered"
    invalid = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=headers,
        json={"baseline": baseline, "current": current},
    )
    assert invalid.status_code == 422
    unauthenticated = client.post("/api/v1/research-evidence-audit/review-actions/generate", json={})
    assert unauthenticated.status_code == 401
