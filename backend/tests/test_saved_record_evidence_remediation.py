import pytest

from tests.conftest import auth_headers


def create_project(client, headers, title):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Remediate saved record evidence"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, *, source_url, stance="supports"):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": source_url,
            "source_title": "Remediation source",
            "publisher": "Example Institute",
            "author": "A. Researcher",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": "The intervention changed measured outcomes.",
            "excerpt": "Measured outcomes changed during evaluation.",
            "stance": stance,
            "contradiction_key": "intervention-outcome" if stance == "contradicts" else None,
            "provenance": {"ingestion_method": "manual"},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_memory(client, headers, project_id, evidence_ids):
    response = client.post(
        "/api/v1/knowledge-memory/user-authored",
        headers=headers,
        json={
            "project_id": project_id,
            "statement": "The intervention improved measured outcomes.",
            "summary": "Intervention remediation record",
            "category": "research_context",
            "confidence": 0.7,
            "source_evidence_ids": evidence_ids,
            "provenance": {"basis": "research review"},
        },
    )
    assert response.status_code == 201
    return response.json()


def get_plan(client, headers, memory_id):
    response = client.get(
        f"/api/v1/knowledge-memory/{memory_id}/evidence-remediation",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_remediation_plan_generates_explainable_priority_actions(client):
    headers = auth_headers(client, email="memory-remediation@example.com")
    project = create_project(client, headers, "Remediation project")
    supporting = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.com/support",
    )
    contradicting = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.com/contradiction",
        stance="contradicts",
    )
    memory = create_memory(
        client,
        headers,
        project["id"],
        [supporting["id"], contradicting["id"], 999999],
    )

    plan = get_plan(client, headers, memory["id"])

    assert plan["memory_id"] == memory["id"]
    assert plan["project_id"] == project["id"]
    assert plan["health"]["classification"] == "contested"
    assert plan["total_actions"] >= 3
    action_types = [item["action_type"] for item in plan["actions"]]
    assert action_types[:2] == ["restore_evidence", "resolve_contradiction"]
    assert "review_evidence" in action_types
    assert all(item["action_key"].startswith("memory-remediation-") for item in plan["actions"])
    assert all(item["rationale"] and item["completion_criteria"] for item in plan["actions"])


def test_remediation_follow_up_requires_confirmation_and_deduplicates(client):
    headers = auth_headers(client, email="memory-remediation-create@example.com")
    project = create_project(client, headers, "Follow-up remediation project")
    memory = create_memory(client, headers, project["id"], [])
    plan = get_plan(client, headers, memory["id"])
    action = next(item for item in plan["actions"] if item["action_type"] == "add_direct_support")
    endpoint = f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/follow-ups"

    denied = client.post(
        endpoint,
        headers=headers,
        json={"action_key": action["action_key"], "confirmed": False},
    )
    assert denied.status_code == 400

    created = client.post(
        endpoint,
        headers=headers,
        json={"action_key": action["action_key"], "confirmed": True},
    )
    assert created.status_code == 200
    assert created.json()["created"] is True

    repeated = client.post(
        endpoint,
        headers=headers,
        json={"action_key": action["action_key"], "confirmed": True},
    )
    assert repeated.status_code == 200
    assert repeated.json() == {
        "created": False,
        "follow_up_id": created.json()["follow_up_id"],
        "action_key": action["action_key"],
    }

    refreshed = get_plan(client, headers, memory["id"])
    refreshed_action = next(item for item in refreshed["actions"] if item["action_key"] == action["action_key"])
    assert refreshed_action["existing_follow_up_id"] == created.json()["follow_up_id"]
    assert refreshed["open_follow_up_count"] == 1


@pytest.mark.parametrize("terminal_status", ["resolved", "dismissed"])
def test_terminal_remediation_follow_up_reopens_same_record(client, terminal_status):
    headers = auth_headers(client, email=f"memory-remediation-reopen-{terminal_status}@example.com")
    project = create_project(client, headers, f"Reopen {terminal_status} remediation project")
    memory = create_memory(client, headers, project["id"], [])
    action = next(
        item
        for item in get_plan(client, headers, memory["id"])["actions"]
        if item["action_type"] == "add_direct_support"
    )
    endpoint = f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/follow-ups"
    created = client.post(
        endpoint,
        headers=headers,
        json={"action_key": action["action_key"], "confirmed": True},
    )
    assert created.status_code == 200
    follow_up_id = created.json()["follow_up_id"]

    update_payload = {
        "status": terminal_status,
        "confirmed": True,
        "note": f"Marking follow-up {terminal_status} for reopening regression coverage.",
    }
    if terminal_status == "resolved":
        update_payload["resolution_notes"] = "The original review cycle was completed."
    terminal = client.patch(
        f"/api/v1/research-follow-up/actions/{follow_up_id}",
        headers=headers,
        json=update_payload,
    )
    assert terminal.status_code == 200
    assert terminal.json()["status"] == terminal_status

    reopened = client.post(
        endpoint,
        headers=headers,
        json={"action_key": action["action_key"], "confirmed": True},
    )
    assert reopened.status_code == 200
    assert reopened.json() == {
        "created": False,
        "follow_up_id": follow_up_id,
        "action_key": action["action_key"],
    }

    queue = client.get(
        f"/api/v1/research-follow-up/projects/{project['id']}",
        headers=headers,
    )
    assert queue.status_code == 200
    follow_up = next(item for item in queue.json()["actions"] if item["id"] == follow_up_id)
    assert follow_up["status"] == "open"
    assert follow_up["resolved_at"] is None
    assert follow_up["resolution_notes"] is None
    assert follow_up["history"][-1]["previous_status"] == terminal_status
    assert follow_up["history"][-1]["new_status"] == "open"
    assert "condition remains active" in follow_up["history"][-1]["note"]


def test_remediation_plan_and_creation_enforce_owner_isolation(client):
    owner_headers = auth_headers(client, email="memory-remediation-owner@example.com")
    other_headers = auth_headers(client, email="memory-remediation-other@example.com")
    project = create_project(client, owner_headers, "Private remediation project")
    memory = create_memory(client, owner_headers, project["id"], [])
    action = get_plan(client, owner_headers, memory["id"])["actions"][0]

    denied_plan = client.get(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation",
        headers=other_headers,
    )
    assert denied_plan.status_code == 404

    denied_create = client.post(
        f"/api/v1/knowledge-memory/{memory['id']}/evidence-remediation/follow-ups",
        headers=other_headers,
        json={"action_key": action["action_key"], "confirmed": True},
    )
    assert denied_create.status_code == 404
