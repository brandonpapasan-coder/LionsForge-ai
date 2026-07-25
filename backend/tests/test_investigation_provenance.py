from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def _investigation(client, headers, title="Provenance"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "How did this investigation change?"},
    )
    assert response.status_code == 201
    return response.json()


def _claim(client, headers, investigation_id, statement="A testable claim"):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def test_provenance_timeline_requires_authentication(client):
    response = client.get(f"{BASE}/1/provenance-timeline")
    assert response.status_code == 401


def test_provenance_timeline_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="provenance-empty@example.com")
    investigation = _investigation(client, headers)

    response = client.get(
        f"{BASE}/{investigation['id']}/provenance-timeline",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["events"] == []
    assert payload["generated_from"] == "stored_investigation_records"
    assert "does not establish truth" in payload["interpretation_notice"]


def test_provenance_timeline_aggregates_stored_categories_and_orders_newest_first(client):
    headers = auth_headers(client, email="provenance-events@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"])

    progress = client.put(
        f"{BASE}/{investigation['id']}/remediation-progress/{claim['id']}",
        headers=headers,
        json={"status": "in_progress", "notes": "Finding a direct source."},
    )
    assert progress.status_code == 200

    evidence = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Primary source",
            "source_url": "https://example.com/source",
            "evidence_type": "primary",
            "relationship": "supports",
            "notes": "Direct test.",
        },
    )
    assert evidence.status_code == 201

    judgment = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "medium",
            "rationale": "The attached source supports the claim.",
            "unresolved_questions": None,
        },
    )
    assert judgment.status_code == 201

    response = client.get(
        f"{BASE}/{investigation['id']}/provenance-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    categories = {event["category"] for event in payload["events"]}
    assert categories == {
        "claim",
        "evidence",
        "validation",
        "remediation_progress",
        "remediation_history",
    }
    assert payload["status"] == "active"
    occurred = [event["occurred_at"] for event in payload["events"]]
    assert occurred == sorted(occurred, reverse=True)
    assert all(event["claim_id"] == claim["id"] for event in payload["events"])
    assert all(event["source_table"] for event in payload["events"])
    validation_event = next(event for event in payload["events"] if event["category"] == "validation")
    assert validation_event["authorship"] == "human_judgment"
    history_event = next(event for event in payload["events"] if event["category"] == "remediation_history")
    assert history_event["action"] == "recorded"


def test_provenance_timeline_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="provenance-owner@example.com")
    investigation = _investigation(client, owner_headers, title="Owner timeline")
    _claim(client, owner_headers, investigation["id"], statement="Owner claim")

    other_headers = auth_headers(client, email="provenance-other@example.com")
    response = client.get(
        f"{BASE}/{investigation['id']}/provenance-timeline",
        headers=other_headers,
    )

    assert response.status_code == 404
