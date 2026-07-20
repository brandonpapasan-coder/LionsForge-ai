from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def create_investigation(client, headers, title="Export review"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What does the stored evidence justify?"},
    )
    assert response.status_code == 201
    return response.json()


def packet(client, headers, investigation_id):
    response = client.get(f"{BASE}/{investigation_id}/evidence-packet", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_empty_evidence_packet_is_conservative_deterministic_and_owner_isolated(client):
    owner = auth_headers(client, email="packet-owner@example.com")
    other = auth_headers(client, email="packet-other@example.com")
    investigation = create_investigation(client, owner)

    first = packet(client, owner, investigation["id"])
    second = packet(client, owner, investigation["id"])

    assert first == second
    assert first["contract_version"] == "1.0"
    assert first["export_format"] == "json"
    assert first["investigation_id"] == investigation["id"]
    assert first["validation_report"]["claims"] == []
    assert first["validation_report"]["synthesis"] is None
    assert all(
        dimension["status"] == "missing"
        for dimension in first["quality_assessment"]["dimensions"]
    )
    assert first["generated_from_stored_state_at"] == first["validation_report"]["generated_from_stored_state_at"]
    assert "human-authored" in first["provenance_notice"]
    assert "does not assign truth" in first["provenance_notice"]
    assert client.get(f"{BASE}/{investigation['id']}/evidence-packet", headers=other).status_code == 404


def test_evidence_packet_preserves_stored_content_authorship_and_order(client):
    headers = auth_headers(client, email="packet-content@example.com")
    investigation = create_investigation(client, headers, title="Auditable packet")

    claim_response = client.post(
        f"{BASE}/{investigation['id']}/claims",
        headers=headers,
        json={"statement": "The primary record supports the cautious conclusion."},
    )
    assert claim_response.status_code == 201
    claim = claim_response.json()

    evidence_response = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Primary record",
            "source_url": "https://example.com/record",
            "evidence_type": "primary",
            "relationship": "supports",
            "notes": "Stored research note.",
        },
    )
    assert evidence_response.status_code == 201

    judgment_response = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "supported",
            "confidence_level": "medium",
            "rationale": "A human reviewer assessed the stored record.",
            "unresolved_questions": "Would an independent source change this judgment?",
        },
    )
    assert judgment_response.status_code == 201

    synthesis_response = client.put(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=headers,
        json={
            "findings": "The stored evidence supports a cautious finding.",
            "limitations": "Only one source type is currently represented.",
            "unresolved_questions": "Independent corroboration remains open.",
        },
    )
    assert synthesis_response.status_code == 200

    exported = packet(client, headers, investigation["id"])
    report = exported["validation_report"]
    assessment = exported["quality_assessment"]

    assert report["title"] == "Auditable packet"
    assert report["claims"][0]["statement"] == "The primary record supports the cautious conclusion."
    assert report["claims"][0]["evidence"][0]["source_title"] == "Primary record"
    assert report["claims"][0]["evidence"][0]["notes"] == "Stored research note."
    assert report["claims"][0]["latest_judgment"]["authorship"] == "user_judgment"
    assert report["synthesis"]["authorship"] == "user_authored"
    assert [dimension["key"] for dimension in assessment["dimensions"]] == [
        "claim_coverage",
        "evidence_coverage",
        "evidence_type_diversity",
        "human_validation_judgments",
        "synthesis_findings",
        "recorded_limitations",
        "unresolved_questions",
    ]
    assert exported["generated_from_stored_state_at"] == report["generated_from_stored_state_at"]
    assert assessment["generated_from_stored_state_at"] == report["generated_from_stored_state_at"]
