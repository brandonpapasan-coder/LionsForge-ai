import hashlib
import json
from copy import deepcopy

from app.api.routes import review_queue_snapshot
from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
REPORT = f"{SNAPSHOT}/compare/report"
RECEIPT = f"{REPORT}/verify/receipt"


def _canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


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


def _report(client, headers) -> dict:
    _create_claim(client, headers, "Existing", "Existing claim")
    prior = client.get(SNAPSHOT, headers=headers).json()
    _create_claim(client, headers, "New", "New claim")
    response = client.post(REPORT, headers=headers, json=prior)
    assert response.status_code == 200
    return response.json()


def test_verification_receipt_requires_authentication(client):
    response = client.post(RECEIPT, json={})
    assert response.status_code == 401


def test_verification_receipt_exports_canonical_artifact_and_headers(client):
    headers = auth_headers(client, email="receipt@example.com")
    report = _report(client, headers)

    response = client.post(RECEIPT, headers=headers, json=report)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == (
        'attachment; filename="lionsforge-comparison-verification-receipt.json"'
    )
    payload = response.json()
    comparison = report["comparison"]
    assert payload["contract_version"] == "1.0"
    assert payload["artifact_type"] == (
        "cross_investigation_review_queue_comparison_verification_receipt"
    )
    assert payload["verified_report_content_sha256"] == report["content_sha256"]
    assert payload["prior_content_sha256"] == comparison["prior_content_sha256"]
    assert payload["current_content_sha256"] == comparison["current_content_sha256"]
    assert payload["added_item_count"] == 1
    assert payload["removed_item_count"] == 0
    assert payload["unchanged_item_count"] == 1
    assert payload["reason_count_deltas"] == {"missing_validation": 1}
    assert payload["investigation_count_delta"] == 1
    assert payload["current_state_checked"] is False
    assert payload["verification_contract_version"] == "1.0"
    assert payload["verification_artifact_type"].endswith("report_verification")
    assert "artifact integrity only" in payload["interpretation_notice"]

    unsigned = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "content_sha256"}
    }
    expected_digest = _canonical_digest(unsigned)
    assert payload["content_sha256"] == expected_digest
    assert response.headers["x-content-sha256"] == expected_digest


def test_verification_receipt_digest_excludes_generated_time(client):
    headers = auth_headers(client, email="receipt-stable@example.com")
    report = _report(client, headers)

    first = client.post(RECEIPT, headers=headers, json=report)
    second = client.post(RECEIPT, headers=headers, json=report)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["content_sha256"] == second.json()["content_sha256"]
    assert first.headers["x-content-sha256"] == second.headers["x-content-sha256"]


def test_verification_receipt_rejects_report_digest_mismatch_without_download_headers(client):
    headers = auth_headers(client, email="receipt-digest@example.com")
    report = _report(client, headers)
    report["content_sha256"] = "0" * 64

    response = client.post(RECEIPT, headers=headers, json=report)

    assert response.status_code == 400
    assert "digest" in response.json()["detail"].lower()
    assert "content-disposition" not in response.headers
    assert "x-content-sha256" not in response.headers


def test_verification_receipt_rejects_unsupported_contract_and_artifact(client):
    headers = auth_headers(client, email="receipt-contract@example.com")
    report = _report(client, headers)

    unsupported = deepcopy(report)
    unsupported["contract_version"] = "2.0"
    assert client.post(RECEIPT, headers=headers, json=unsupported).status_code == 422

    wrong_artifact = deepcopy(report)
    wrong_artifact["artifact_type"] = "other"
    assert client.post(RECEIPT, headers=headers, json=wrong_artifact).status_code == 422


def test_verification_receipt_does_not_read_current_queue_state(client, monkeypatch):
    headers = auth_headers(client, email="receipt-offline@example.com")
    report = _report(client, headers)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("receipt export must not read current queue state")

    monkeypatch.setattr(
        review_queue_snapshot,
        "cross_investigation_review_queue",
        fail_if_called,
    )

    response = client.post(RECEIPT, headers=headers, json=report)

    assert response.status_code == 200
    assert response.json()["current_state_checked"] is False
