from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def _investigation(client, headers, title="Progress history"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "How did remediation work change?"},
    )
    assert response.status_code == 201
    return response.json()


def _claim(client, headers, investigation_id, statement="A claim requiring evidence"):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def _put(client, headers, investigation_id, claim_id, status, notes=None):
    return client.put(
        f"{BASE}/{investigation_id}/remediation-progress/{claim_id}",
        headers=headers,
        json={"status": status, "notes": notes},
    )


def _history(client, headers, investigation_id, claim_id):
    return client.get(
        f"{BASE}/{investigation_id}/remediation-progress/{claim_id}/history",
        headers=headers,
    )


def test_remediation_progress_history_requires_authentication(client):
    response = client.get(f"{BASE}/1/remediation-progress/1/history")
    assert response.status_code == 401


def test_remediation_progress_history_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="progress-history-empty@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"])

    response = _history(client, headers, investigation["id"], claim["id"])

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["events"] == []
    assert payload["generated_from"] == "append_only_user_progress_history"
    assert "append-only" in payload["interpretation_notice"]


def test_remediation_progress_history_records_initial_and_repeated_updates(client):
    headers = auth_headers(client, email="progress-history-events@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"])
    statuses = ["not_started", "in_progress", "blocked", "ready_for_review", "dismissed"]

    for status in statuses:
        response = _put(
            client,
            headers,
            investigation["id"],
            claim["id"],
            status,
            f"  Note for {status}.  ",
        )
        assert response.status_code == 200

    response = _history(client, headers, investigation["id"], claim["id"])
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == len(statuses)
    assert [event["status"] for event in events] == list(reversed(statuses))
    assert [event["notes"] for event in events] == [
        f"Note for {status}." for status in reversed(statuses)
    ]
    assert all(event["authorship"] == "user_authored" for event in events)
    assert all(event["action_type_snapshot"] == "attach_initial_evidence" for event in events)
    assert len({event["event_id"] for event in events}) == len(statuses)


def test_remediation_progress_history_snapshots_are_immutable_and_survive_supersession(client):
    headers = auth_headers(client, email="progress-history-superseded@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"], "A claim that becomes supported")

    assert _put(
        client,
        headers,
        investigation["id"],
        claim["id"],
        "in_progress",
        "Initial evidence search.",
    ).status_code == 200

    evidence = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Supporting source",
            "source_url": "https://example.com/support",
            "evidence_type": "primary",
            "relationship": "supports",
        },
    )
    assert evidence.status_code == 201
    judgment = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "high",
            "rationale": "The reviewed source supports the claim.",
        },
    )
    assert judgment.status_code == 201

    current = client.get(
        f"{BASE}/{investigation['id']}/remediation-progress",
        headers=headers,
    ).json()["entries"][0]
    assert current["current_action"] is None

    history = _history(client, headers, investigation["id"], claim["id"])
    assert history.status_code == 200
    event = history.json()["events"][0]
    assert event["status"] == "in_progress"
    assert event["notes"] == "Initial evidence search."
    assert event["action_type_snapshot"] == "attach_initial_evidence"
    assert event["priority_snapshot"] == 3


def test_remediation_progress_history_is_owner_isolated(client):
    owner = auth_headers(client, email="progress-history-owner@example.com")
    other = auth_headers(client, email="progress-history-other@example.com")
    investigation = _investigation(client, owner)
    claim = _claim(client, owner, investigation["id"])
    assert _put(
        client,
        owner,
        investigation["id"],
        claim["id"],
        "blocked",
        "Waiting on source access.",
    ).status_code == 200

    owner_response = _history(client, owner, investigation["id"], claim["id"])
    other_response = _history(client, other, investigation["id"], claim["id"])

    assert owner_response.status_code == 200
    assert owner_response.json()["events"][0]["status"] == "blocked"
    assert other_response.status_code == 404
