from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
EXPECTED_KEYS = [
    "claim_coverage",
    "evidence_coverage",
    "evidence_type_diversity",
    "human_validation_judgments",
    "synthesis_findings",
    "recorded_limitations",
    "unresolved_questions",
]


def create_investigation(client, headers):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": "Quality review", "research_question": "What conclusion is justified?"},
    )
    assert response.status_code == 201
    return response.json()


def assessment(client, headers, investigation_id):
    response = client.get(f"{BASE}/{investigation_id}/quality-assessment", headers=headers)
    assert response.status_code == 200
    return response.json()


def statuses(payload):
    return {dimension["key"]: dimension["status"] for dimension in payload["dimensions"]}


def test_empty_quality_assessment_is_conservative_deterministic_and_owner_isolated(client):
    owner = auth_headers(client, email="quality-owner@example.com")
    other = auth_headers(client, email="quality-other@example.com")
    investigation = create_investigation(client, owner)

    first = assessment(client, owner, investigation["id"])
    second = assessment(client, owner, investigation["id"])

    assert [dimension["key"] for dimension in first["dimensions"]] == EXPECTED_KEYS
    assert all(value == "missing" for value in statuses(first).values())
    assert len(first["recommendations"]) == len(EXPECTED_KEYS)
    assert first == second
    assert "not a truth score" in first["interpretation_notice"]
    assert client.get(f"{BASE}/{investigation['id']}/quality-assessment", headers=other).status_code == 404


def test_quality_assessment_tracks_partial_and_complete_stored_state(client):
    headers = auth_headers(client, email="quality-progress@example.com")
    investigation = create_investigation(client, headers)
    first_claim = client.post(
        f"{BASE}/{investigation['id']}/claims",
        headers=headers,
        json={"statement": "The first claim is supported."},
    ).json()
    second_claim = client.post(
        f"{BASE}/{investigation['id']}/claims",
        headers=headers,
        json={"statement": "The second claim needs review."},
    ).json()
    client.post(
        f"{BASE}/claims/{first_claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Primary record",
            "source_url": "https://example.com/primary",
            "evidence_type": "primary",
            "relationship": "supports",
        },
    )
    client.post(
        f"{BASE}/claims/{first_claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "medium",
            "rationale": "Human reviewer judgment.",
        },
    )
    client.put(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=headers,
        json={"findings": "A cautious finding."},
    )

    partial = assessment(client, headers, investigation["id"])
    partial_status = statuses(partial)
    assert partial_status["claim_coverage"] == "complete"
    assert partial_status["evidence_coverage"] == "partial"
    assert partial_status["evidence_type_diversity"] == "partial"
    assert partial_status["human_validation_judgments"] == "partial"
    assert partial_status["synthesis_findings"] == "complete"
    assert partial_status["recorded_limitations"] == "missing"
    assert partial_status["unresolved_questions"] == "missing"

    client.post(
        f"{BASE}/claims/{second_claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Secondary analysis",
            "source_url": "https://example.com/secondary",
            "evidence_type": "secondary",
            "relationship": "neutral",
        },
    )
    client.post(
        f"{BASE}/claims/{second_claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "inconclusive",
            "confidence_level": "low",
            "rationale": "Human reviewer judgment remains cautious.",
        },
    )
    client.put(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=headers,
        json={
            "findings": "A cautious finding.",
            "limitations": "Coverage remains limited.",
            "unresolved_questions": "What additional evidence could change the conclusion?",
        },
    )

    complete = assessment(client, headers, investigation["id"])
    assert all(value == "complete" for value in statuses(complete).values())
    assert complete["recommendations"] == []
    judgment_dimension = next(
        dimension for dimension in complete["dimensions"] if dimension["key"] == "human_validation_judgments"
    )
    assert judgment_dimension["counts"] == {"claims": 2, "judgments": 2, "current_judgments": 2}
