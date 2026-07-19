from tests.conftest import auth_headers


def create_evidence(client, headers, *, title, claim, stance="supports", key=None, provenance=None, source_url=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "source_url": source_url,
            "source_title": title,
            "source_type": "secondary",
            "claim": claim,
            "excerpt": f"Excerpt for {claim}",
            "stance": stance,
            "contradiction_key": key,
            "provenance": provenance or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_provenance_ledger_empty_state(client):
    headers = auth_headers(client, email="provenance-empty@example.com")
    response = client.get("/api/v1/research-evidence-provenance/ledger", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "total_evidence": 0,
        "total_events": 0,
        "unresolved_contradictions": 0,
        "superseded_claims": 0,
        "missing_source_metadata": 0,
    }
    assert body["entries"] == []
    assert "do not verify" in body["disclaimer"]


def test_provenance_ledger_orders_creation_review_and_supersession(client):
    headers = auth_headers(client, email="provenance-events@example.com")
    first = create_evidence(
        client,
        headers,
        title="Initial source",
        claim="Initial claim",
        key="shared-question",
        source_url="https://example.com/initial",
    )
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{first['id']}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Resolve the conflicting interpretation."},
    )
    assert reviewed.status_code == 200
    create_evidence(
        client,
        headers,
        title="Revised source",
        claim="Revised claim",
        stance="contradicts",
        key="shared-question",
        provenance={"supersedes_evidence_id": first["id"]},
        source_url="https://example.com/revised",
    )

    response = client.get("/api/v1/research-evidence-provenance/ledger", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_evidence"] == 2
    assert body["summary"]["total_events"] == 4
    assert body["summary"]["unresolved_contradictions"] == 1
    assert body["summary"]["superseded_claims"] == 1
    assert [entry["event_type"] for entry in body["entries"]] == [
        "evidence_created",
        "review_recorded",
        "evidence_created",
        "claim_superseded",
    ]
    assert body["entries"][1]["reviewer_notes"] == "Resolve the conflicting interpretation."
    assert body["entries"][3]["supersedes_evidence_id"] == first["id"]

    first_events = [entry for entry in body["entries"] if entry["evidence_id"] == first["id"]]
    assert first_events
    assert {entry["fingerprint"] for entry in first_events} == {first["fingerprint"]}
    assert {entry["source_url"] for entry in first_events} == {"https://example.com/initial"}
    for entry in first_events:
        assert 0.0 <= entry["credibility_score"] <= 1.0
        assert 0.0 <= entry["freshness_score"] <= 1.0
        assert 0.0 <= entry["confidence_score"] <= 1.0


def test_provenance_ledger_warns_for_missing_non_user_source_url(client):
    headers = auth_headers(client, email="provenance-warning@example.com")
    created = create_evidence(client, headers, title="Unlinked source", claim="A claim without a URL")

    body = client.get("/api/v1/research-evidence-provenance/ledger", headers=headers).json()
    assert body["summary"]["missing_source_metadata"] == 1
    assert body["entries"][0]["warning"] == "Source URL is missing for non-user evidence."
    assert body["entries"][0]["source_url"] is None
    assert body["entries"][0]["publisher"] is None
    assert body["entries"][0]["author"] is None
    assert body["entries"][0]["published_at"] is None
    assert body["entries"][0]["fingerprint"] == created["fingerprint"]


def test_provenance_ledger_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="provenance-owner@example.com")
    other_headers = auth_headers(client, email="provenance-other@example.com")
    create_evidence(
        client,
        owner_headers,
        title="Private source",
        claim="Private claim",
        source_url="https://example.com/private",
    )

    owner = client.get("/api/v1/research-evidence-provenance/ledger", headers=owner_headers)
    other = client.get("/api/v1/research-evidence-provenance/ledger", headers=other_headers)
    assert owner.status_code == 200
    assert other.status_code == 200
    assert owner.json()["summary"]["total_evidence"] == 1
    assert other.json()["summary"]["total_evidence"] == 0
