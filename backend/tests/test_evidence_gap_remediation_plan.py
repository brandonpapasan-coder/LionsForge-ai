from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def _create_investigation(client, headers, title="Remediation plan"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What research work remains?"},
    )
    assert response.status_code == 201
    return response.json()


def _create_claim(client, headers, investigation_id, statement):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def _create_evidence(client, headers, claim_id, relationship, suffix):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": f"Source {suffix}",
            "source_url": f"https://example.com/{suffix}",
            "evidence_type": "primary",
            "relationship": relationship,
            "notes": f"Recorded {relationship} evidence.",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_judgment(client, headers, claim_id, status="supported"):
    response = client.post(
        f"{BASE}/claims/{claim_id}/judgments",
        headers=headers,
        json={
            "validation_status": status,
            "confidence_level": "medium",
            "rationale": "Human review of the currently recorded evidence.",
            "unresolved_questions": None,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_remediation_plan_requires_authentication(client):
    response = client.get(f"{BASE}/1/remediation-plan")
    assert response.status_code == 401


def test_remediation_plan_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="remediation-empty@example.com")
    investigation = _create_investigation(client, headers)

    response = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["actions"] == []
    assert payload["action_counts"] == {
        "resolve_contradiction": 0,
        "collect_direct_evidence": 0,
        "attach_initial_evidence": 0,
        "refresh_human_review": 0,
    }
    assert payload["generated_from"] == "validation_map_stored_inputs"


def test_remediation_plan_prioritizes_recorded_gaps_deterministically(client):
    headers = auth_headers(client, email="remediation-priority@example.com")
    investigation = _create_investigation(client, headers)
    stale_supported = _create_claim(client, headers, investigation["id"], "Supported but stale")
    unreviewed = _create_claim(client, headers, investigation["id"], "No evidence")
    insufficient = _create_claim(client, headers, investigation["id"], "Context only")
    contested = _create_claim(client, headers, investigation["id"], "Conflicting evidence")

    stale_evidence = _create_evidence(client, headers, stale_supported["id"], "supports", "stale")
    _create_judgment(client, headers, stale_supported["id"])
    changed = client.patch(
        f"{BASE}/evidence/{stale_evidence['id']}",
        headers=headers,
        json={
            "source_title": "Updated supporting source",
            "source_url": "https://example.com/stale-updated",
            "evidence_type": "primary",
            "relationship": "supports",
            "notes": "The supporting source metadata changed after review.",
        },
    )
    assert changed.status_code == 200

    _create_evidence(client, headers, insufficient["id"], "neutral", "context")
    _create_evidence(client, headers, contested["id"], "supports", "conflict-support")
    _create_evidence(client, headers, contested["id"], "contradicts", "conflict-contradiction")

    first = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=headers)
    second = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=headers)

    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert payload["status"] == "action_required"
    assert [item["claim_id"] for item in payload["actions"]] == [
        contested["id"],
        insufficient["id"],
        unreviewed["id"],
        stale_supported["id"],
    ]
    assert [item["priority"] for item in payload["actions"]] == [1, 2, 3, 4]
    assert [item["action_type"] for item in payload["actions"]] == [
        "resolve_contradiction",
        "collect_direct_evidence",
        "attach_initial_evidence",
        "refresh_human_review",
    ]
    assert payload["actions"][0]["source_requirements"]
    assert payload["actions"][3]["source_requirements"] == []
    assert payload["actions"][3]["review_refresh_required"] is True
    assert all(item["priority_rule"] for item in payload["actions"])
    assert all(item["stored_inputs"] for item in payload["actions"])


def test_remediation_plan_returns_complete_for_current_supported_claims(client):
    headers = auth_headers(client, email="remediation-complete@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"], "Current supported claim")
    _create_evidence(client, headers, claim["id"], "supports", "complete")
    _create_judgment(client, headers, claim["id"])

    response = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["actions"] == []
    assert "do not invent sources, deadlines, confidence" in payload["interpretation_notice"]


def test_remediation_plan_uses_only_recorded_inputs_and_is_owner_isolated(client):
    owner = auth_headers(client, email="remediation-owner@example.com")
    other = auth_headers(client, email="remediation-other@example.com")
    investigation = _create_investigation(client, owner)
    claim = _create_claim(client, owner, investigation["id"], "Private unsupported claim")

    response = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=owner)
    unauthorized = client.get(f"{BASE}/{investigation['id']}/remediation-plan", headers=other)

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert payload["actions"][0]["claim_id"] == claim["id"]
    assert "recorded_gap=" in " ".join(payload["actions"][0]["stored_inputs"])
    assert "deadline=" not in serialized
    assert "confidence=" not in serialized
    assert "https://example.com/" not in serialized
    assert unauthorized.status_code == 404
