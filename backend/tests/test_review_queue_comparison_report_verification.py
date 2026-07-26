from copy import deepcopy

from app.api.routes import review_queue_snapshot
from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
REPORT = f"{SNAPSHOT}/compare/report"
VERIFY = f"{REPORT}/verify"


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


def test_report_verification_requires_authentication(client):
    response = client.post(VERIFY, json={})
    assert response.status_code == 401


def test_report_verification_returns_deterministic_preserved_metadata(client):
    headers = auth_headers(client, email="verify-report@example.com")
    report = _report(client, headers)

    response = client.post(VERIFY, headers=headers, json=report)

    assert response.status_code == 200
    payload = response.json()
    comparison = report["comparison"]
    assert payload["contract_version"] == "1.0"
    assert payload["artifact_type"] == (
        "cross_investigation_review_queue_comparison_report_verification"
    )
    assert payload["valid"] is True
    assert payload["supplied_content_sha256"] == report["content_sha256"]
    assert payload["recomputed_content_sha256"] == report["content_sha256"]
    assert payload["prior_content_sha256"] == comparison["prior_content_sha256"]
    assert payload["current_content_sha256"] == comparison["current_content_sha256"]
    assert payload["added_item_count"] == 1
    assert payload["removed_item_count"] == 0
    assert payload["unchanged_item_count"] == 1
    assert payload["reason_count_deltas"] == {"missing_validation": 1}
    assert payload["investigation_count_delta"] == 1
    assert payload["current_state_checked"] is False
    assert "canonical digest only" in payload["interpretation_notice"]
    assert "current queue state" in payload["interpretation_notice"]


def test_report_verification_rejects_digest_mismatch(client):
    headers = auth_headers(client, email="verify-report-digest@example.com")
    report = _report(client, headers)
    report["content_sha256"] = "0" * 64

    response = client.post(VERIFY, headers=headers, json=report)

    assert response.status_code == 400
    assert "digest" in response.json()["detail"].lower()


def test_report_verification_rejects_unsupported_contract_and_artifact(client):
    headers = auth_headers(client, email="verify-report-contract@example.com")
    report = _report(client, headers)

    unsupported = deepcopy(report)
    unsupported["contract_version"] = "2.0"
    assert client.post(VERIFY, headers=headers, json=unsupported).status_code == 422

    wrong_artifact = deepcopy(report)
    wrong_artifact["artifact_type"] = "other"
    assert client.post(VERIFY, headers=headers, json=wrong_artifact).status_code == 422


def test_report_verification_does_not_read_current_queue_state(client, monkeypatch):
    headers = auth_headers(client, email="verify-report-offline@example.com")
    report = _report(client, headers)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("verification must not read current queue state")

    monkeypatch.setattr(
        review_queue_snapshot,
        "cross_investigation_review_queue",
        fail_if_called,
    )

    response = client.post(VERIFY, headers=headers, json=report)

    assert response.status_code == 200
    assert response.json()["current_state_checked"] is False


def test_report_verification_rejects_malformed_nested_contract(client):
    headers = auth_headers(client, email="verify-report-malformed@example.com")
    report = _report(client, headers)
    del report["comparison"]["prior_content_sha256"]

    response = client.post(VERIFY, headers=headers, json=report)

    assert response.status_code == 422
