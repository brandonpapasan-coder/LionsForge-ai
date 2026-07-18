from tests.conftest import auth_headers
from tests.test_saved_record_evidence_remediation import (
    create_evidence,
    create_memory,
    create_project,
    get_plan,
)


def create_follow_up(client, headers, memory_id, action_key):
    response = client.post(
        f"/api/v1/knowledge-memory/{memory_id}/evidence-remediation/follow-ups",
        headers=headers,
        json={"action_key": action_key, "confirmed": True},
    )
    assert response.status_code == 200
    return response.json()


def get_verification(client, headers, memory_id):
    response = client.get(
        f"/api/v1/knowledge-memory/{memory_id}/evidence-remediation/verification",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_verification_reports_unresolved_criteria_and_blocks_resolution(client):
    headers = auth_headers(client, email="remediation-verification-unresolved@example.com")
    project = create_project(client, headers, "Verification unresolved project")
    memory = create_memory(client, headers, project["id"], [])
    action = next(
        item for item in get_plan(client, headers, memory["id"])["actions"]
        if item["action_type"] == "add_direct_support"
    )
    follow_up = create_follow_up(client, headers, memory["id"], action["action_key"])

    verification = get_verification(client, headers, memory["id"])
    item = next(entry for entry in verification["actions"] if entry["action_key"] == action["action_key"])
    assert item["follow_up_id"] == follow_up["follow_up_id"]
    assert item["status"] == "unresolved"
    assert item["passed_count"] == 0
    assert all(criterion["passed"] is False for criterion in item["criteria"])

    denied = client.post(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/verification/resolve",
        headers=headers,
        json={
            "action_key": action["action_key"],
            "confirmed": True,
            "resolution_notes": "Attempted before criteria passed.",
        },
    )
    assert denied.status_code == 409


def test_ready_action_requires_confirmation_and_records_resolution_history(client):
    headers = auth_headers(client, email="remediation-verification-ready@example.com")
    project = create_project(client, headers, "Verification ready project")
    memory = create_memory(client, headers, project["id"], [])
    action = next(
        item for item in get_plan(client, headers, memory["id"])["actions"]
        if item["action_type"] == "add_direct_support"
    )
    follow_up = create_follow_up(client, headers, memory["id"], action["action_key"])

    evidence = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.com/verified-direct-support",
    )
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={
            "validation_status": "approved",
            "reviewer_notes": "Directly supports the saved record statement.",
        },
    )
    assert reviewed.status_code == 200
    revised = client.patch(
        f"/api/v1/knowledge-memory/{memory['id']}",
        headers=headers,
        json={"source_evidence_ids": [evidence["id"]]},
    )
    assert revised.status_code == 200

    verification = get_verification(client, headers, memory["id"])
    item = next(entry for entry in verification["actions"] if entry["action_key"] == action["action_key"])
    assert item["status"] == "ready_for_resolution"
    assert item["passed_count"] == item["total_count"] == 2
    assert all(criterion["passed"] is True for criterion in item["criteria"])

    endpoint = f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/verification/resolve"
    unconfirmed = client.post(
        endpoint,
        headers=headers,
        json={
            "action_key": action["action_key"],
            "confirmed": False,
            "resolution_notes": "Direct support verified.",
        },
    )
    assert unconfirmed.status_code == 400

    resolved = client.post(
        endpoint,
        headers=headers,
        json={
            "action_key": action["action_key"],
            "confirmed": True,
            "resolution_notes": "Direct support was added, reviewed, and linked.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True
    assert resolved.json()["follow_up_id"] == follow_up["follow_up_id"]
    assert resolved.json()["status"] == "resolved"

    queue = client.get(
        f"/api/v1/research-follow-up/projects/{project['id']}",
        headers=headers,
    )
    assert queue.status_code == 200
    queue_item = next(item for item in queue.json()["actions"] if item["id"] == follow_up["follow_up_id"])
    assert queue_item["resolution_notes"] == "Direct support was added, reviewed, and linked."
    assert queue_item["history"][-1]["previous_status"] == "open"
    assert queue_item["history"][-1]["new_status"] == "resolved"


def test_verification_and_resolution_enforce_owner_isolation(client):
    owner_headers = auth_headers(client, email="remediation-verification-owner@example.com")
    other_headers = auth_headers(client, email="remediation-verification-other@example.com")
    project = create_project(client, owner_headers, "Private verification project")
    memory = create_memory(client, owner_headers, project["id"], [])
    action = get_plan(client, owner_headers, memory["id"])["actions"][0]
    create_follow_up(client, owner_headers, memory["id"], action["action_key"])

    hidden = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/verification",
        headers=other_headers,
    )
    assert hidden.status_code == 404

    denied = client.post(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/verification/resolve",
        headers=other_headers,
        json={
            "action_key": action["action_key"],
            "confirmed": True,
            "resolution_notes": "Not the owner.",
        },
    )
    assert denied.status_code == 404
