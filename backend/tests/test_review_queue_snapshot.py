import hashlib
import json

from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"


def _create_claim(client, headers, title: str, statement: str) -> None:
    investigation = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What needs review?"},
    )
    assert investigation.status_code == 201
    claim = client.post(
        f"{BASE}/{investigation.json()['id']}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert claim.status_code == 201


def _unsigned_digest(payload: dict) -> str:
    unsigned = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "content_sha256"}
    }
    canonical = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_snapshot_requires_authentication(client):
    response = client.get(SNAPSHOT)
    assert response.status_code == 401


def test_snapshot_exports_empty_state_with_integrity_headers(client):
    headers = auth_headers(client, email="snapshot-empty@example.com")
    response = client.get(SNAPSHOT, headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == (
        'attachment; filename="lionsforge-review-queue-snapshot.json"'
    )
    payload = response.json()
    assert payload["queue"]["status"] == "empty"
    assert payload["queue"]["items"] == []
    assert payload["reason_counts"] == {}
    assert payload["investigation_count"] == 0
    assert payload["content_sha256"] == _unsigned_digest(payload)
    assert response.headers["x-content-sha256"] == payload["content_sha256"]
    assert "integrity only" in payload["interpretation_notice"]


def test_snapshot_digest_is_stable_for_unchanged_queue_and_changes_with_state(client):
    headers = auth_headers(client, email="snapshot-stable@example.com")
    _create_claim(client, headers, "Stable queue", "Claim awaiting review")

    first = client.get(SNAPSHOT, headers=headers)
    second = client.get(SNAPSHOT, headers=headers)
    assert first.status_code == second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["content_sha256"] == second_payload["content_sha256"]
    assert first_payload["content_sha256"] == _unsigned_digest(first_payload)
    assert first_payload["reason_counts"] == {"missing_validation": 1}
    assert first_payload["investigation_count"] == 1

    _create_claim(client, headers, "Changed queue", "Another claim awaiting review")
    changed_payload = client.get(SNAPSHOT, headers=headers).json()
    assert changed_payload["content_sha256"] != first_payload["content_sha256"]
    assert changed_payload["reason_counts"] == {"missing_validation": 2}
    assert changed_payload["investigation_count"] == 2


def test_snapshot_isolates_owner_records(client):
    first_headers = auth_headers(client, email="snapshot-owner-one@example.com")
    _create_claim(client, first_headers, "Owner one", "Owner one claim")

    second_headers = auth_headers(client, email="snapshot-owner-two@example.com")
    _create_claim(client, second_headers, "Owner two", "Owner two claim")

    payload = client.get(SNAPSHOT, headers=first_headers).json()
    assert payload["queue"]["item_count"] == 1
    assert payload["queue"]["items"][0]["investigation_title"] == "Owner one"
    assert payload["queue"]["items"][0]["claim_statement"] == "Owner one claim"
