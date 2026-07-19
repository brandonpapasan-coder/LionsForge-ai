from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def create_investigation(client, headers):
    response = client.post(BASE, headers=headers, json={"title": "Synthesis review", "research_question": "What conclusion is justified?"})
    assert response.status_code == 201
    return response.json()


def test_synthesis_normalization_and_owner_isolation(client):
    owner = auth_headers(client, email="synthesis-owner@example.com")
    other = auth_headers(client, email="synthesis-other@example.com")
    investigation = create_investigation(client, owner)
    empty = client.put(f"{BASE}/{investigation['id']}/synthesis", headers=owner, json={"findings": "  ", "limitations": "\n"})
    assert empty.status_code == 422
    saved = client.put(
        f"{BASE}/{investigation['id']}/synthesis",
        headers=owner,
        json={"findings": "  A limited conclusion.  ", "limitations": " Incomplete coverage. ", "unresolved_questions": " More evidence? "},
    )
    assert saved.status_code == 200
    assert saved.json()["findings"] == "A limited conclusion."
    assert saved.json()["authorship"] == "user_authored"
    assert client.get(f"{BASE}/{investigation['id']}/synthesis", headers=other).status_code == 404
    assert client.get(f"{BASE}/{investigation['id']}/validation-report", headers=other).status_code == 404


def test_report_is_deterministic_and_labels_human_judgment(client):
    headers = auth_headers(client, email="report-owner@example.com")
    investigation = create_investigation(client, headers)
    client.put(f"{BASE}/{investigation['id']}/synthesis", headers=headers, json={"findings": "A cautious finding."})
    claim = client.post(f"{BASE}/{investigation['id']}/claims", headers=headers, json={"statement": "The claim is supported."}).json()
    client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={"source_title": "Primary record", "source_url": "https://example.com/primary", "evidence_type": "primary", "relationship": "supports"},
    )
    client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={"validation_status": "supported", "confidence_level": "medium", "rationale": "Reviewer judgment."},
    )
    first = client.get(f"{BASE}/{investigation['id']}/validation-report", headers=headers).json()
    second = client.get(f"{BASE}/{investigation['id']}/validation-report", headers=headers).json()
    first.pop("generated_from_stored_state_at")
    second.pop("generated_from_stored_state_at")
    assert first == second
    assert first["claims"][0]["latest_judgment"]["authorship"] == "user_judgment"
    assert "does not present user judgments as automated truth" in first["interpretation_notice"]
