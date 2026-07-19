from tests.conftest import auth_headers


BASE = "/api/v1/investigations"


def _create_investigation(client, headers):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": "Synthesis review", "research_question": "What does the evidence support?"},
    )
    assert response.status_code == 201
    return response.json()


def _create_claim(client, headers, investigation_id):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": "The available evidence supports a limited finding."},
    )
    assert response.status_code == 201
    return response.json()


def _create_evidence(client, headers, claim_id, relationship="supports"):
    response = client.post(
        f"{BASE}/claims/{claim_id}/evidence",
        headers=headers,
        json={
            "source_title": f"{relationship.title()} source",
            "source_url": f"https://example.com/{relationship}",
            "evidence_type": "primary",
            "relationship": relationship,
            "notes": "Auditable source note.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_synthesis_is_normalized_and_owner_isolated(client):
    owner = auth_headers(client, email="synthesis-owner@example.com")
    other = auth_headers(client, email="synthesis-other@example.com")
    investigation = _create_investigation(client, owner)

    response = client.patch(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=owner,
        json={
            "findings": "  Evidence supports a limited finding.  ",
            "limitations": "   ",
            "unresolved_questions": "What additional primary evidence exists?",
        },
    )
    assert response.status_code == 200
    assert response.json()["findings"] == "Evidence supports a limited finding."
    assert response.json()["limitations"] is None

    assert client.patch(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=other,
        json={"findings": "No access"},
    ).status_code == 404
    assert client.get(
        f"{BASE}/{investigation['id']}/validation-report", headers=other
    ).status_code == 404


def test_validation_report_is_deterministic_and_auditable(client):
    headers = auth_headers(client, email="report-owner@example.com")
    investigation = _create_investigation(client, headers)
    claim = _create_claim(client, headers, investigation["id"])
    _create_evidence(client, headers, claim["id"], "supports")
    _create_evidence(client, headers, claim["id"], "contradicts")

    client.patch(
        f"{BASE}/claims/{claim['id']}/assessment",
        headers=headers,
        json={"confidence_level": "medium", "confidence_rationale": "Evidence is mixed."},
    )
    client.patch(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=headers,
        json={
            "findings": "The evidence supports only a limited conclusion.",
            "limitations": "One source conflicts with the finding.",
            "unresolved_questions": "Can the contradiction be independently resolved?",
        },
    )

    first = client.get(f"{BASE}/{investigation['id']}/validation-report", headers=headers)
    second = client.get(f"{BASE}/{investigation['id']}/validation-report", headers=headers)
    assert first.status_code == 200
    assert first.json() == second.json()
    report = first.json()
    assert report["automated_truth_determination"] is False
    assert report["user_authored_assessments"] is True
    assert report["unresolved_contradiction_count"] == 1
    assert report["claims"][0]["supporting_count"] == 1
    assert report["claims"][0]["contradicting_count"] == 1
    assert [item["relationship"] for item in report["claims"][0]["evidence"]] == [
        "supports",
        "contradicts",
    ]
