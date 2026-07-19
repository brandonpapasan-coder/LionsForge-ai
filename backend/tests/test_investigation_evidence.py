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


def create_evidence(client, headers, claim_id):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": "Primary source",
            "source_url": "https://example.com/source",
            "evidence_type": "primary",
            "relationship": "supports",
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
