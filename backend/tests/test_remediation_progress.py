from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def _investigation(client, headers, title="Progress ledger"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What work remains?"},
    )
    assert response.status_code == 201
    return response.json()


def _claim(client, headers, investigation_id, statement):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def _evidence(client, headers, claim_id, relationship, suffix):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": f"Source {suffix}",
            "source_url": f"https://example.com/{suffix}",
            "evidence_type": "primary",
            "relationship": relationship,
        },
    )
    assert response.status_code == 201
    return response.json()


def _put(client, headers, investigation_id, claim_id, status, notes=None):
    return client.put(
        f"{BASE}/{investigation_id}/remediation-progress/{claim_id}",
        headers=headers,
        json={"status": status, "notes": notes},
    )


def test_remediation_progress_requires_authentication(client):
    assert client.get(f"{BASE}/1/remediation-progress").status_code == 401
    assert (
        client.put(
            f"{BASE}/1/remediation-progress/1",
            json={"status": "in_progress"},
        ).status_code
        == 401
    )


def test_remediation_progress_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="progress-empty@example.com")
    investigation = _investigation(client, headers)

    response = client.get(
        f"{BASE}/{investigation['id']}/remediation-progress",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["entries"] == []
    assert payload["generated_from"] == "user_progress_and_current_remediation_plan"
    assert "user-authored" in payload["interpretation_notice"]


def test_remediation_progress_creates_and_updates_every_allowed_status(client):
    headers = auth_headers(client, email="progress-statuses@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"], "A claim needing initial evidence")
    statuses = ["not_started", "in_progress", "blocked", "ready_for_review", "dismissed"]

    for status in statuses:
        response = _put(
            client,
            headers,
            investigation["id"],
            claim["id"],
            status,
            f"  User note for {status}.  ",
        )
        assert response.status_code == 200
        entry = response.json()["entries"][0]
        assert entry["status"] == status
        assert entry["notes"] == f"User note for {status}."
        assert entry["authorship"] == "user_authored"
        assert entry["is_stale"] is False
        assert entry["current_action"]["action_type"] == "attach_initial_evidence"
        assert entry["action_type_snapshot"] == "attach_initial_evidence"

    invalid = _put(
        client,
        headers,
        investigation["id"],
        claim["id"],
        "complete",
    )
    assert invalid.status_code == 422


def test_remediation_progress_detects_changed_action_and_preserves_history(client):
    headers = auth_headers(client, email="progress-stale@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"], "A changing claim")

    created = _put(
        client,
        headers,
        investigation["id"],
        claim["id"],
        "in_progress",
        "Finding an initial source.",
    )
    assert created.status_code == 200
    assert created.json()["entries"][0]["is_stale"] is False

    _evidence(client, headers, claim["id"], "neutral", "context")
    stale = client.get(
        f"{BASE}/{investigation['id']}/remediation-progress",
        headers=headers,
    )
    entry = stale.json()["entries"][0]
    assert entry["is_stale"] is True
    assert entry["action_type_snapshot"] == "attach_initial_evidence"
    assert entry["current_action"]["action_type"] == "collect_direct_evidence"
    assert any("action type changed" in reason for reason in entry["stale_reasons"])
    assert any("underlying claim, evidence" in reason for reason in entry["stale_reasons"])


def test_remediation_progress_keeps_record_when_action_no_longer_exists(client):
    headers = auth_headers(client, email="progress-superseded@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"], "A claim that becomes supported")
    assert _put(client, headers, investigation["id"], claim["id"], "ready_for_review").status_code == 200

    _evidence(client, headers, claim["id"], "supports", "support")
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

    payload = client.get(
        f"{BASE}/{investigation['id']}/remediation-progress",
        headers=headers,
    ).json()
    entry = payload["entries"][0]
    assert entry["status"] == "ready_for_review"
    assert entry["current_action"] is None
    assert entry["is_stale"] is True
    assert entry["stale_reasons"] == ["No current remediation action exists for this claim."]

    rejected = _put(client, headers, investigation["id"], claim["id"], "dismissed")
    assert rejected.status_code == 409


def test_remediation_progress_is_deterministic_and_owner_isolated(client):
    owner = auth_headers(client, email="progress-owner@example.com")
    other = auth_headers(client, email="progress-other@example.com")
    investigation = _investigation(client, owner)
    unreviewed = _claim(client, owner, investigation["id"], "Unreviewed claim")
    contested = _claim(client, owner, investigation["id"], "Contested claim")
    _evidence(client, owner, contested["id"], "contradicts", "contradiction")

    assert _put(client, owner, investigation["id"], unreviewed["id"], "not_started").status_code == 200
    assert _put(client, owner, investigation["id"], contested["id"], "blocked").status_code == 200

    first = client.get(f"{BASE}/{investigation['id']}/remediation-progress", headers=owner)
    second = client.get(f"{BASE}/{investigation['id']}/remediation-progress", headers=owner)
    unauthorized_get = client.get(
        f"{BASE}/{investigation['id']}/remediation-progress",
        headers=other,
    )
    unauthorized_put = _put(
        client,
        other,
        investigation["id"],
        contested["id"],
        "in_progress",
    )

    assert first.status_code == 200
    assert first.json() == second.json()
    assert [entry["claim_id"] for entry in first.json()["entries"]] == [
        contested["id"],
        unreviewed["id"],
    ]
    assert unauthorized_get.status_code == 404
    assert unauthorized_put.status_code == 404
