from datetime import datetime, timedelta

from tests.conftest import auth_headers
from tests.test_research_review_actions_api import build_changed_packets


def generate_action(client, headers):
    project, baseline, current = build_changed_packets(client, headers)
    response = client.post(
        "/api/v1/research-evidence-audit/review-actions/generate",
        headers=headers,
        json={"baseline": baseline, "current": current},
    )
    assert response.status_code == 200
    return project, response.json()["actions"][0]


def test_follow_up_tracker_updates_metadata_and_orders_urgent_overdue_actions(client):
    headers = auth_headers(client, email="follow-up-order@example.com")
    project, action = generate_action(client, headers)
    due_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
    updated = client.patch(
        f"/api/v1/research-follow-up/actions/{action['id']}",
        headers=headers,
        json={
            "priority": "urgent",
            "due_at": due_at,
            "owner_notes": "Assigned to evidence reviewer.",
            "confirmed": True,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["priority"] == "urgent"
    assert body["overdue"] is True
    assert body["owner_notes"] == "Assigned to evidence reviewer."

    queue = client.get(f"/api/v1/research-follow-up/projects/{project['id']}", headers=headers)
    assert queue.status_code == 200
    queue_body = queue.json()
    assert queue_body["overdue"] == 1
    assert queue_body["actions"][0]["id"] == action["id"]


def test_follow_up_tracker_requires_resolution_notes_and_audits_transitions(client):
    headers = auth_headers(client, email="follow-up-resolution@example.com")
    _, action = generate_action(client, headers)
    denied = client.patch(
        f"/api/v1/research-follow-up/actions/{action['id']}",
        headers=headers,
        json={"status": "resolved", "confirmed": True},
    )
    assert denied.status_code == 422

    resolved = client.patch(
        f"/api/v1/research-follow-up/actions/{action['id']}",
        headers=headers,
        json={
            "status": "resolved",
            "resolution_notes": "Source metadata was verified and the dependent conclusion was rechecked.",
            "note": "Review completed.",
            "confirmed": True,
        },
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None
    assert body["history"][-1]["new_status"] == "resolved"
    assert body["history"][-1]["note"] == "Review completed."


def test_follow_up_tracker_supports_blocked_filters_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="follow-up-owner@example.com")
    other_headers = auth_headers(client, email="follow-up-other@example.com")
    project, action = generate_action(client, owner_headers)
    blocked = client.patch(
        f"/api/v1/research-follow-up/actions/{action['id']}",
        headers=owner_headers,
        json={"status": "blocked", "note": "Waiting for source access.", "confirmed": True},
    )
    assert blocked.status_code == 200

    filtered = client.get(
        f"/api/v1/research-follow-up/projects/{project['id']}?status=blocked",
        headers=owner_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["blocked"] == 1
    assert all(item["status"] == "blocked" for item in filtered.json()["actions"])

    hidden = client.get(f"/api/v1/research-follow-up/projects/{project['id']}", headers=other_headers)
    assert hidden.status_code == 404
    forbidden = client.patch(
        f"/api/v1/research-follow-up/actions/{action['id']}",
        headers=other_headers,
        json={"priority": "high", "confirmed": True},
    )
    assert forbidden.status_code == 404
