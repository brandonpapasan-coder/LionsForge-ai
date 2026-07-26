from copy import deepcopy

from app.api.routes import review_queue_snapshot
from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
REPORT = f"{SNAPSHOT}/compare/report"
RECEIPT = f"{REPORT}/verify/receipt"
VALIDATE = f"{RECEIPT}/validate"


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


def _receipt(client, headers) -> dict:
    _create_claim(client, headers, "Existing", "Existing claim")
    prior = client.get(SNAPSHOT, headers=headers).json()
    _create_claim(client, headers, "New", "New claim")
    report_response = client.post(REPORT, headers=headers, json=prior)
    assert report_response.status_code == 200
    receipt_response = client.post(
        RECEIPT,
        headers=headers,
        json=report_response.json(),
    )
    assert receipt_response.status_code == 200
    return receipt_response.json()


def test_receipt_validation_requires_authentication(client):
    response = client.post(VALIDATE, json={})
    assert response.status_code == 401


def test_receipt_validation_returns_deterministic_bound_metadata(client):
    headers = auth_headers(client, email="validate-receipt@example.com")
    receipt = _receipt(client, headers)

    response = client.post(VALIDATE, headers=headers, json=receipt)

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "1.0"
    assert payload["artifact_type"] == (
        "cross_investigation_review_queue_comparison_verification_receipt_validation"
    )
    assert payload["valid"] is True
    assert payload["supplied_content_sha256"] == receipt["content_sha256"]
    assert payload["recomputed_content_sha256"] == receipt["content_sha256"]
    assert payload["verified_report_content_sha256"] == receipt[
        "verified_report_content_sha256"
    ]
    assert payload["prior_content_sha256"] == receipt["prior_content_sha256"]
    assert payload["current_content_sha256"] == receipt["current_content_sha256"]
    assert payload["added_item_count"] == 1
    assert payload["removed_item_count"] == 0
    assert payload["unchanged_item_count"] == 1
    assert payload["reason_count_deltas"] == {"missing_validation": 1}
    assert payload["investigation_count_delta"] == 1
    assert payload["verification_contract_version"] == "1.0"
    assert payload["verification_artifact_type"].endswith("report_verification")
    assert payload["current_state_checked"] is False
    assert "canonical digest only" in payload["interpretation_notice"]
    assert "current queue state" in payload["interpretation_notice"]


def test_receipt_validation_rejects_digest_mismatch(client):
    headers = auth_headers(client, email="validate-receipt-digest@example.com")
    receipt = _receipt(client, headers)
    receipt["content_sha256"] = "0" * 64

    response = client.post(VALIDATE, headers=headers, json=receipt)

    assert response.status_code == 400
    assert "digest" in response.json()["detail"].lower()


def test_receipt_validation_rejects_unsupported_contract_and_artifact(client):
    headers = auth_headers(client, email="validate-receipt-contract@example.com")
    receipt = _receipt(client, headers)

    unsupported = deepcopy(receipt)
    unsupported["contract_version"] = "2.0"
    assert client.post(VALIDATE, headers=headers, json=unsupported).status_code == 422

    wrong_artifact = deepcopy(receipt)
    wrong_artifact["artifact_type"] = "other"
    assert client.post(VALIDATE, headers=headers, json=wrong_artifact).status_code == 422


def test_receipt_validation_rejects_malformed_contract(client):
    headers = auth_headers(client, email="validate-receipt-malformed@example.com")
    receipt = _receipt(client, headers)
    del receipt["verified_report_content_sha256"]

    response = client.post(VALIDATE, headers=headers, json=receipt)

    assert response.status_code == 422


def test_receipt_validation_does_not_read_current_queue_state(client, monkeypatch):
    headers = auth_headers(client, email="validate-receipt-offline@example.com")
    receipt = _receipt(client, headers)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("receipt validation must not read current queue state")

    monkeypatch.setattr(
        review_queue_snapshot,
        "cross_investigation_review_queue",
        fail_if_called,
    )

    response = client.post(VALIDATE, headers=headers, json=receipt)

    assert response.status_code == 200
    assert response.json()["current_state_checked"] is False
