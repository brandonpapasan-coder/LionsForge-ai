from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def _create_investigation(client, headers):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": "Ledger review", "research_question": "What does the record support?"},
    )
    assert response.status_code == 201
    return response.json()


def _create_claim(client, headers, investigation_id):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": "The available evidence supports the claim."},
    )
    assert response.status_code == 201
    return response.json()


def _create_evidence(client, headers, claim_id):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": "Primary record",
            "source_url": "https://example.com/record",
            "evidence_type": "primary",
            "relationship": "supports",
            "notes": "Direct record.",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_judgment(client, headers, claim_id, rationale="The primary record supports this assessment."):
    return client.post(
        f"{BASE}/claims/{claim_id}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "high",
            "rationale": rationale,
            "unresolved_questions": "Confirm the publication context.",
        },
    )


def test_claim_judgments_are_append_only_and_ordered(client):
    headers = auth_headers(client, email="ledger-owner@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"])
    _create_evidence(client, headers, claim["id"])

    first = _create_judgment(client, headers, claim["id"])
    second = _create_judgment(client, headers, claim["id"], "A second independent review reached the same result.")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["is_stale"] is False

    listing = client.get(f"{BASE}/claims/{claim['id']}/judgments", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [second.json()["id"], first.json()["id"]]
    assert all(item["reviewer_id"] > 0 for item in listing.json())
    assert all(item["reviewed_at"] for item in listing.json())


def test_claim_judgment_access_is_owner_isolated(client):
    owner = auth_headers(client, email="ledger-private-owner@example.com")
    other = auth_headers(client, email="ledger-private-other@example.com")
    investigation = _create_investigation(client, owner)
    claim = _create_claim(client, owner, investigation["id"])

    assert _create_judgment(client, other, claim["id"]).status_code == 404
    assert client.get(f"{BASE}/claims/{claim['id']}/judgments", headers=other).status_code == 404


def test_judgment_validation_rejects_invalid_or_blank_values(client):
    headers = auth_headers(client, email="ledger-validation@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"])

    invalid = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "proven",
            "confidence_level": "certain",
            "rationale": "   ",
        },
    )
    assert invalid.status_code == 422


def test_judgment_becomes_stale_after_claim_or_evidence_changes(client):
    headers = auth_headers(client, email="ledger-stale@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"])
    evidence = _create_evidence(client, headers, claim["id"])
    judgment = _create_judgment(client, headers, claim["id"])
    assert judgment.status_code == 201
    assert judgment.json()["is_stale"] is False

    changed_claim = client.patch(
        f"{BASE}/claims/{claim['id']}",
        headers=headers,
        json={"statement": "The revised claim is narrower than the original."},
    )
    assert changed_claim.status_code == 200

    listing = client.get(f"{BASE}/claims/{claim['id']}/judgments", headers=headers)
    assert listing.status_code == 200
    assert listing.json()[0]["is_stale"] is True

    fresh = _create_judgment(client, headers, claim["id"], "The revised claim remains supported.")
    assert fresh.status_code == 201
    assert fresh.json()["is_stale"] is False

    changed_evidence = client.patch(
        f"{BASE}/evidence/{evidence['id']}",
        headers=headers,
        json={
            "source_title": "Revised primary record",
            "source_url": "https://example.com/revised-record",
            "evidence_type": "primary",
            "relationship": "contradicts",
            "notes": "The revised record changes the relationship.",
        },
    )
    assert changed_evidence.status_code == 200

    listing = client.get(f"{BASE}/claims/{claim['id']}/judgments", headers=headers)
    assert listing.status_code == 200
    assert all(item["is_stale"] is True for item in listing.json())
