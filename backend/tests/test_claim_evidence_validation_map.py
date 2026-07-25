from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def _create_investigation(client, headers, title="Validation map"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What does the recorded evidence establish?"},
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


def test_validation_map_requires_authentication(client):
    response = client.get(f"{BASE}/1/validation-map")
    assert response.status_code == 401


def test_validation_map_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="validation-map-empty@example.com")
    investigation = _create_investigation(client, headers)

    response = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["claims"] == []
    assert payload["summary_counts"] == {
        "supported": 0,
        "contested": 0,
        "insufficient": 0,
        "unreviewed": 0,
    }
    assert payload["generated_from"] == "stored_evidence_rules"
    assert payload["unresolved_gaps"] == ["No material claims are recorded for this investigation."]


def test_validation_map_derives_all_statuses_and_relationships(client):
    headers = auth_headers(client, email="validation-map-statuses@example.com")
    investigation = _create_investigation(client, headers)
    supported = _create_claim(client, headers, investigation["id"], "Supported claim")
    contested = _create_claim(client, headers, investigation["id"], "Contested claim")
    insufficient = _create_claim(client, headers, investigation["id"], "Context-only claim")
    unreviewed = _create_claim(client, headers, investigation["id"], "No-evidence claim")

    _create_evidence(client, headers, supported["id"], "supports", "support")
    _create_evidence(client, headers, contested["id"], "supports", "mixed-support")
    _create_evidence(client, headers, contested["id"], "contradicts", "mixed-contradiction")
    _create_evidence(client, headers, insufficient["id"], "neutral", "context")

    response = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert [item["sequence"] for item in payload["claims"]] == [1, 2, 3, 4]
    by_id = {item["claim_id"]: item for item in payload["claims"]}
    assert by_id[supported["id"]]["status"] == "supported"
    assert by_id[contested["id"]]["status"] == "contested"
    assert by_id[insufficient["id"]]["status"] == "insufficient"
    assert by_id[unreviewed["id"]]["status"] == "unreviewed"
    assert payload["summary_counts"] == {
        "supported": 1,
        "contested": 1,
        "insufficient": 1,
        "unreviewed": 1,
    }

    contested_links = by_id[contested["id"]]["evidence_links"]
    assert [item["relationship"] for item in contested_links] == ["supporting", "contradicting"]
    assert [item["stored_relationship"] for item in contested_links] == ["supports", "contradicts"]
    assert all("maps directly" in item["classification_rule"] for item in contested_links)
    assert by_id[contested["id"]]["relationship_counts"] == {
        "supporting": 1,
        "contradicting": 1,
        "contextual": 0,
    }
    assert by_id[unreviewed["id"]]["human_review"]["status"] == "not_reviewed"
    assert "do not establish objective truth" in payload["interpretation_notice"]


def test_validation_map_surfaces_current_and_stale_human_review(client):
    headers = auth_headers(client, email="validation-map-review@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"], "Reviewed claim")
    evidence = _create_evidence(client, headers, claim["id"], "supports", "reviewed")

    judgment = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "high",
            "rationale": "The recorded primary source supports the claim.",
            "unresolved_questions": "Confirm whether a newer source changes the conclusion.",
        },
    )
    assert judgment.status_code == 201

    current = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=headers).json()
    assert current["claims"][0]["human_review"]["status"] == "current"
    assert current["claims"][0]["human_review"]["authorship"] == "user_judgment"

    changed = client.patch(
        f"{BASE}/evidence/{evidence['id']}",
        headers=headers,
        json={
            "source_title": "Revised source",
            "source_url": "https://example.com/revised",
            "evidence_type": "primary",
            "relationship": "contradicts",
            "notes": "The revised source changes the relationship.",
        },
    )
    assert changed.status_code == 200

    stale = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=headers).json()
    assert stale["claims"][0]["status"] == "contested"
    assert stale["claims"][0]["human_review"]["status"] == "stale"
    assert any("Refresh the human validation judgment" in gap for gap in stale["claims"][0]["unresolved_gaps"])


def test_validation_map_is_deterministic_and_owner_isolated(client):
    owner = auth_headers(client, email="validation-map-owner@example.com")
    other = auth_headers(client, email="validation-map-other@example.com")
    investigation = _create_investigation(client, owner)
    claim = _create_claim(client, owner, investigation["id"], "Private claim")
    _create_evidence(client, owner, claim["id"], "supports", "private")

    first = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=owner)
    second = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=owner)
    unauthorized = client.get(f"{BASE}/{investigation['id']}/validation-map", headers=other)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert unauthorized.status_code == 404
