from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def create_investigation(client, headers, title="Education-linked research"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What should the evidence establish?"},
    )
    assert response.status_code == 201
    return response.json()


def create_claim(client, headers, investigation_id, statement="The claim requires validation."):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def test_empty_investigation_recommends_thesis_construction(client):
    headers = auth_headers(client, email="education-gap-empty@example.com")
    investigation = create_investigation(client, headers)

    response = client.get(
        f"{BASE}/{investigation['id']}/education-recommendations",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["completion_authority"] == "adaptive_assessment_only"
    assert body["recommendation_count"] == 1
    assert body["recommendations"][0]["gap_type"] == "missing_claims"
    assert body["recommendations"][0]["lesson_slug"] == "research-thesis-construction"


def test_missing_evidence_and_validation_generate_explainable_recommendations(client):
    headers = auth_headers(client, email="education-gap-claim@example.com")
    investigation = create_investigation(client, headers)
    create_claim(client, headers, investigation["id"])

    response = client.get(
        f"{BASE}/{investigation['id']}/education-recommendations",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    gap_types = {item["gap_type"] for item in body["recommendations"]}
    assert {"missing_evidence", "low_claim_confidence", "missing_validation_judgment"} <= gap_types
    assert all(item["reason"] for item in body["recommendations"])
    assert all("correct" not in item for item in body["recommendations"])


def test_contradictions_unassessed_sources_and_unresolved_questions_are_mapped(client):
    headers = auth_headers(client, email="education-gap-mixed@example.com")
    investigation = create_investigation(client, headers)
    claim = create_claim(client, headers, investigation["id"])

    evidence_response = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Contradicting source",
            "source_url": "https://example.com/contradiction",
            "evidence_type": "primary",
            "relationship": "contradicts",
        },
    )
    assert evidence_response.status_code == 201

    judgment_response = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "mixed",
            "confidence_level": "low",
            "rationale": "The record is internally inconsistent.",
            "unresolved_questions": "Which source is more reliable?",
        },
    )
    assert judgment_response.status_code == 201

    response = client.get(
        f"{BASE}/{investigation['id']}/education-recommendations",
        headers=headers,
    )

    assert response.status_code == 200
    gap_types = {item["gap_type"] for item in response.json()["recommendations"]}
    assert "contradictory_evidence" in gap_types
    assert "unassessed_credibility" in gap_types
    assert "unresolved_questions" in gap_types
    assert "inconclusive_validation" in gap_types


def test_recommendations_are_owner_isolated_and_do_not_change_education_progress(client):
    owner = auth_headers(client, email="education-gap-owner@example.com")
    other = auth_headers(client, email="education-gap-other@example.com")
    investigation = create_investigation(client, owner)
    create_claim(client, owner, investigation["id"])

    before = client.get("/api/v1/education", headers=owner)
    assert before.status_code == 200

    assert client.get(
        f"{BASE}/{investigation['id']}/education-recommendations",
        headers=other,
    ).status_code == 404

    recommendation_response = client.get(
        f"{BASE}/{investigation['id']}/education-recommendations",
        headers=owner,
    )
    assert recommendation_response.status_code == 200

    after = client.get("/api/v1/education", headers=owner)
    assert after.status_code == 200
    assert after.json()["completed_lessons"] == before.json()["completed_lessons"]
    assert after.json()["assessed_lessons"] == before.json()["assessed_lessons"]
    assert recommendation_response.json()["completion_authority"] == "adaptive_assessment_only"
