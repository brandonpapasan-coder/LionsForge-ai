from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def create_investigation(client, headers, title="Source review"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What does the evidence establish?"},
    )
    assert response.status_code == 201
    return response.json()


def create_claim(client, headers, investigation_id, statement="The source supports the conclusion."):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, claim_id, relationship="supports", title="Primary source"):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": title,
            "source_url": "https://example.com/source",
            "evidence_type": "primary",
            "relationship": relationship,
            "notes": "Directly addresses the claim.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_claim_and_evidence_crud(client):
    headers = auth_headers(client, email="claim-owner@example.com")
    investigation = create_investigation(client, headers)
    claim = create_claim(client, headers, investigation["id"])

    listing = client.get(f"{BASE}/{investigation['id']}/claims", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [claim["id"]]

    updated_claim = client.patch(
        f"{BASE}/claims/{claim['id']}",
        headers=headers,
        json={"statement": "Updated claim statement."},
    )
    assert updated_claim.status_code == 200
    assert updated_claim.json()["statement"] == "Updated claim statement."

    evidence = create_evidence(client, headers, claim["id"])
    evidence_listing = client.get(f"{BASE}/claims/{claim['id']}/evidence", headers=headers)
    assert evidence_listing.status_code == 200
    assert evidence_listing.json()[0]["id"] == evidence["id"]

    updated_evidence = client.patch(
        f"{BASE}/evidence/{evidence['id']}",
        headers=headers,
        json={
            "source_title": "Revised source",
            "source_url": "https://example.com/revised",
            "evidence_type": "dataset",
            "relationship": "contradicts",
            "notes": None,
        },
    )
    assert updated_evidence.status_code == 200
    assert updated_evidence.json()["relationship"] == "contradicts"

    assert client.delete(f"{BASE}/evidence/{evidence['id']}", headers=headers).status_code == 204
    assert client.delete(f"{BASE}/claims/{claim['id']}", headers=headers).status_code == 204


def test_claims_and_evidence_are_owner_isolated(client):
    owner = auth_headers(client, email="claim-private-owner@example.com")
    other = auth_headers(client, email="claim-private-other@example.com")
    investigation = create_investigation(client, owner)
    claim = create_claim(client, owner, investigation["id"])
    evidence = create_evidence(client, owner, claim["id"])

    assert client.get(f"{BASE}/{investigation['id']}/claims", headers=other).status_code == 404
    assert client.patch(f"{BASE}/claims/{claim['id']}", headers=other, json={"statement": "No"}).status_code == 404
    assert client.delete(f"{BASE}/claims/{claim['id']}", headers=other).status_code == 404
    assert client.get(f"{BASE}/claims/{claim['id']}/evidence", headers=other).status_code == 404
    assert client.delete(f"{BASE}/evidence/{evidence['id']}", headers=other).status_code == 404


def test_invalid_claim_and_evidence_values_are_rejected(client):
    headers = auth_headers(client, email="claim-validation@example.com")
    investigation = create_investigation(client, headers)

    assert client.post(f"{BASE}/{investigation['id']}/claims", headers=headers, json={"statement": "   "}).status_code == 422
    claim = create_claim(client, headers, investigation["id"])

    invalid_url = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Bad source",
            "source_url": "javascript:alert(1)",
            "evidence_type": "primary",
            "relationship": "supports",
        },
    )
    assert invalid_url.status_code == 422

    invalid_enums = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Bad classification",
            "source_url": "https://example.com",
            "evidence_type": "rumor",
            "relationship": "proves",
        },
    )
    assert invalid_enums.status_code == 422


def test_deleting_claim_cascades_evidence(client):
    headers = auth_headers(client, email="claim-cascade@example.com")
    investigation = create_investigation(client, headers)
    claim = create_claim(client, headers, investigation["id"])
    evidence = create_evidence(client, headers, claim["id"])

    assert client.delete(f"{BASE}/claims/{claim['id']}", headers=headers).status_code == 204
    assert client.delete(f"{BASE}/evidence/{evidence['id']}", headers=headers).status_code == 404


def test_assessments_require_rationale_and_are_owner_isolated(client):
    owner = auth_headers(client, email="assessment-owner@example.com")
    other = auth_headers(client, email="assessment-other@example.com")
    investigation = create_investigation(client, owner)
    claim = create_claim(client, owner, investigation["id"])
    evidence = create_evidence(client, owner, claim["id"])

    missing_claim_rationale = client.patch(
        f"{BASE}/claims/{claim['id']}/assessment",
        headers=owner,
        json={"confidence_level": "high", "confidence_rationale": "   "},
    )
    assert missing_claim_rationale.status_code == 422

    invalid_evidence_rating = client.patch(
        f"{BASE}/evidence/{evidence['id']}/assessment",
        headers=owner,
        json={"credibility_rating": "certain", "credibility_rationale": "Reviewed source."},
    )
    assert invalid_evidence_rating.status_code == 422

    claim_assessment = client.patch(
        f"{BASE}/claims/{claim['id']}/assessment",
        headers=owner,
        json={"confidence_level": "medium", "confidence_rationale": "Support exists, but a contradiction remains."},
    )
    assert claim_assessment.status_code == 200
    assert claim_assessment.json()["confidence_level"] == "medium"

    evidence_assessment = client.patch(
        f"{BASE}/evidence/{evidence['id']}/assessment",
        headers=owner,
        json={"credibility_rating": "high", "credibility_rationale": "Primary source with direct observations."},
    )
    assert evidence_assessment.status_code == 200
    assert evidence_assessment.json()["credibility_rating"] == "high"

    assert client.patch(
        f"{BASE}/claims/{claim['id']}/assessment",
        headers=other,
        json={"confidence_level": "low", "confidence_rationale": "Unauthorized."},
    ).status_code == 404
    assert client.get(f"{BASE}/{investigation['id']}/validation-summary", headers=other).status_code == 404


def test_validation_summaries_count_relationships_and_confidence(client):
    headers = auth_headers(client, email="summary-owner@example.com")
    investigation = create_investigation(client, headers)
    assessed_claim = create_claim(client, headers, investigation["id"], "Assessed claim")
    unassessed_claim = create_claim(client, headers, investigation["id"], "Unassessed claim")

    supporting = create_evidence(client, headers, assessed_claim["id"], "supports", "Supporting source")
    create_evidence(client, headers, assessed_claim["id"], "contradicts", "Contradicting source")
    create_evidence(client, headers, assessed_claim["id"], "neutral", "Neutral source")

    assert client.patch(
        f"{BASE}/claims/{assessed_claim['id']}/assessment",
        headers=headers,
        json={"confidence_level": "medium", "confidence_rationale": "Mixed evidence requires caution."},
    ).status_code == 200
    assert client.patch(
        f"{BASE}/evidence/{supporting['id']}/assessment",
        headers=headers,
        json={"credibility_rating": "high", "credibility_rationale": "Direct primary documentation."},
    ).status_code == 200

    claim_summary = client.get(f"{BASE}/claims/{assessed_claim['id']}/summary", headers=headers)
    assert claim_summary.status_code == 200
    assert claim_summary.json() == {
        "claim_id": assessed_claim["id"],
        "confidence_level": "medium",
        "supporting_count": 1,
        "contradicting_count": 1,
        "neutral_count": 1,
        "assessed_evidence_count": 1,
        "total_evidence_count": 3,
        "has_unresolved_contradiction": True,
    }

    investigation_summary = client.get(
        f"{BASE}/{investigation['id']}/validation-summary", headers=headers
    )
    assert investigation_summary.status_code == 200
    body = investigation_summary.json()
    assert body["claim_count"] == 2
    assert body["assessed_claim_count"] == 1
    assert body["medium_confidence_count"] == 1
    assert body["low_confidence_count"] == 0
    assert body["high_confidence_count"] == 0
    assert body["unresolved_contradiction_count"] == 1
    assert {item["claim_id"] for item in body["claims"]} == {
        assessed_claim["id"],
        unassessed_claim["id"],
    }
