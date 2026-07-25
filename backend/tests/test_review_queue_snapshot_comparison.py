import hashlib
import json
from copy import deepcopy

from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
COMPARE = f"{SNAPSHOT}/compare"


def _create_claim(client, headers, title: str, statement: str) -> None:
    investigation = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What changed?"},
    )
    assert investigation.status_code == 201
    claim = client.post(
        f"{BASE}/{investigation.json()['id']}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert claim.status_code == 201


def _digest(snapshot: dict) -> str:
    unsigned = {
        key: value
        for key, value in snapshot.items()
        if key not in {"generated_at", "content_sha256"}
    }
    canonical = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_comparison_requires_authentication(client):
    response = client.post(COMPARE, json={})
    assert response.status_code == 401


def test_comparison_rejects_digest_mismatch(client):
    headers = auth_headers(client, email="compare-digest@example.com")
    snapshot = client.get(SNAPSHOT, headers=headers).json()
    snapshot["content_sha256"] = "0" * 64

    response = client.post(COMPARE, headers=headers, json=snapshot)
    assert response.status_code == 400
    assert "digest" in response.json()["detail"].lower()


def test_comparison_rejects_unsupported_contract_and_artifact(client):
    headers = auth_headers(client, email="compare-contract@example.com")
    snapshot = client.get(SNAPSHOT, headers=headers).json()

    unsupported = deepcopy(snapshot)
    unsupported["contract_version"] = "2.0"
    assert client.post(COMPARE, headers=headers, json=unsupported).status_code == 422

    wrong_artifact = deepcopy(snapshot)
    wrong_artifact["artifact_type"] = "other"
    assert client.post(COMPARE, headers=headers, json=wrong_artifact).status_code == 422


def test_comparison_reports_unchanged_and_added_items(client):
    headers = auth_headers(client, email="compare-added@example.com")
    _create_claim(client, headers, "Existing", "Existing claim")
    prior = client.get(SNAPSHOT, headers=headers).json()

    unchanged = client.post(COMPARE, headers=headers, json=prior)
    assert unchanged.status_code == 200
    unchanged_payload = unchanged.json()
    assert len(unchanged_payload["unchanged_items"]) == 1
    assert unchanged_payload["added_items"] == []
    assert unchanged_payload["removed_items"] == []
    assert unchanged_payload["reason_count_deltas"] == {"missing_validation": 0}
    assert unchanged_payload["investigation_count_delta"] == 0

    _create_claim(client, headers, "New", "New claim")
    changed = client.post(COMPARE, headers=headers, json=prior)
    assert changed.status_code == 200
    payload = changed.json()
    assert len(payload["unchanged_items"]) == 1
    assert len(payload["added_items"]) == 1
    assert payload["added_items"][0]["claim_statement"] == "New claim"
    assert payload["removed_items"] == []
    assert payload["reason_count_deltas"] == {"missing_validation": 1}
    assert payload["investigation_count_delta"] == 1
    assert "workflow state only" in payload["interpretation_notice"]


def test_comparison_reports_removed_item_and_empty_current_state(client):
    headers = auth_headers(client, email="compare-removed@example.com")
    prior = client.get(SNAPSHOT, headers=headers).json()
    synthetic = {
        "item_key": "999:999:missing_validation",
        "investigation_id": 999,
        "investigation_title": "Prior-only investigation",
        "investigation_status": "open",
        "claim_id": 999,
        "claim_statement": "Prior-only claim",
        "reason_type": "missing_validation",
        "workflow_priority": 4,
        "reason": "No human validation judgment is stored for this claim.",
        "stored_inputs": ["judgment_count=0"],
        "latest_relevant_at": "2026-07-25T00:00:00Z",
        "source_tables": ["investigation_claims"],
        "source_record_ids": [999],
    }
    prior["queue"]["status"] = "active"
    prior["queue"]["item_count"] = 1
    prior["queue"]["items"] = [synthetic]
    prior["reason_counts"] = {"missing_validation": 1}
    prior["investigation_count"] = 1
    prior["content_sha256"] = _digest(prior)

    response = client.post(COMPARE, headers=headers, json=prior)
    assert response.status_code == 200
    payload = response.json()
    assert payload["added_items"] == []
    assert payload["unchanged_items"] == []
    assert payload["removed_items"] == [synthetic]
    assert payload["reason_count_deltas"] == {"missing_validation": -1}
    assert payload["investigation_count_delta"] == -1


def test_comparison_uses_only_current_owner_queue(client):
    first_headers = auth_headers(client, email="compare-owner-one@example.com")
    prior = client.get(SNAPSHOT, headers=first_headers).json()

    second_headers = auth_headers(client, email="compare-owner-two@example.com")
    _create_claim(client, second_headers, "Other owner", "Other owner claim")

    response = client.post(COMPARE, headers=first_headers, json=prior)
    assert response.status_code == 200
    payload = response.json()
    assert payload["added_items"] == []
    assert payload["current_investigation_count"] == 0
