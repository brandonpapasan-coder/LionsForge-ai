from copy import deepcopy

from app.api.routes import review_queue_snapshot
from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
REPORT = f"{SNAPSHOT}/compare/report"
RECEIPT = f"{REPORT}/verify/receipt"
VALIDATE = f"{BASE}/review-queue/artifacts/validate"


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


def _receipt(client, headers, report: dict | None = None) -> dict:
    source_report = report or _report(client, headers)
    response = client.post(RECEIPT, headers=headers, json=source_report)
    assert response.status_code == 200
    return response.json()


def test_artifact_integrity_requires_authentication(client):
    response = client.post(VALIDATE, json={})
    assert response.status_code == 401


def test_artifact_integrity_dispatches_comparison_report(client):
    headers = auth_headers(client, email="artifact-report@example.com")
    report = _report(client, headers)

    response = client.post(VALIDATE, headers=headers, json=report)

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "1.0"
    assert payload["artifact_type"] == (
        "cross_investigation_review_queue_artifact_integrity_result"
    )
    assert payload["detected_artifact_type"] == report["artifact_type"]
    assert payload["valid"] is True
    assert payload["current_state_checked"] is False
    validation = payload["validation"]
    assert validation["artifact_type"].endswith("report_verification")
    assert validation["recomputed_content_sha256"] == report["content_sha256"]
    assert validation["prior_content_sha256"] == report["comparison"][
        "prior_content_sha256"
    ]
    assert validation["current_content_sha256"] == report["comparison"][
        "current_content_sha256"
    ]


def test_artifact_integrity_dispatches_verification_receipt(client):
    headers = auth_headers(client, email="artifact-receipt@example.com")
    report = _report(client, headers)
    receipt = _receipt(client, headers, report)

    response = client.post(VALIDATE, headers=headers, json=receipt)

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_artifact_type"] == receipt["artifact_type"]
    assert payload["valid"] is True
    assert payload["current_state_checked"] is False
    validation = payload["validation"]
    assert validation["artifact_type"].endswith("receipt_validation")
    assert validation["recomputed_content_sha256"] == receipt["content_sha256"]
    assert validation["verified_report_content_sha256"] == report["content_sha256"]


def test_artifact_integrity_rejects_missing_and_unsupported_types(client):
    headers = auth_headers(client, email="artifact-type@example.com")

    missing = client.post(VALIDATE, headers=headers, json={"contract_version": "1.0"})
    unsupported = client.post(
        VALIDATE,
        headers=headers,
        json={"contract_version": "1.0", "artifact_type": "other"},
    )

    assert missing.status_code == 422
    assert missing.json()["detail"] == "Artifact type is required"
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"] == "Artifact type is unsupported"


def test_artifact_integrity_rejects_invalid_contract_and_digest(client):
    headers = auth_headers(client, email="artifact-invalid@example.com")
    report = _report(client, headers)

    unsupported_version = deepcopy(report)
    unsupported_version["contract_version"] = "2.0"
    version_response = client.post(
        VALIDATE,
        headers=headers,
        json=unsupported_version,
    )
    assert version_response.status_code == 422
    assert "contract" in version_response.json()["detail"].lower()

    bad_digest = deepcopy(report)
    bad_digest["content_sha256"] = "0" * 64
    digest_response = client.post(VALIDATE, headers=headers, json=bad_digest)
    assert digest_response.status_code == 400
    assert "digest" in digest_response.json()["detail"].lower()


def test_artifact_integrity_does_not_read_current_queue_state(client, monkeypatch):
    headers = auth_headers(client, email="artifact-offline@example.com")
    report = _report(client, headers)
    receipt = _receipt(client, headers, report)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("artifact validation must not read current queue state")

    monkeypatch.setattr(
        review_queue_snapshot,
        "cross_investigation_review_queue",
        fail_if_called,
    )

    report_response = client.post(VALIDATE, headers=headers, json=report)
    receipt_response = client.post(VALIDATE, headers=headers, json=receipt)

    assert report_response.status_code == 200
    assert receipt_response.status_code == 200
    assert report_response.json()["current_state_checked"] is False
    assert receipt_response.json()["current_state_checked"] is False
