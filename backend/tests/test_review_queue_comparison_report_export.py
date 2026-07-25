import hashlib
import json

from tests.conftest import auth_headers

BASE = "/api/v1/investigations"
SNAPSHOT = f"{BASE}/review-queue/snapshot"
COMPARE = f"{SNAPSHOT}/compare"
REPORT = f"{COMPARE}/report"


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


def _canonical_digest(payload: dict, excluded: set[str]) -> str:
    unsigned = {key: value for key, value in payload.items() if key not in excluded}
    canonical = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_report_export_requires_authentication(client):
    response = client.post(REPORT, json={})
    assert response.status_code == 401


def test_report_export_matches_verified_comparison_and_digest(client):
    headers = auth_headers(client, email="report-export@example.com")
    _create_claim(client, headers, "Existing", "Existing claim")
    prior = client.get(SNAPSHOT, headers=headers).json()
    _create_claim(client, headers, "New", "New claim")

    comparison = client.post(COMPARE, headers=headers, json=prior)
    report_response = client.post(REPORT, headers=headers, json=prior)

    assert comparison.status_code == 200
    assert report_response.status_code == 200
    assert report_response.headers["content-type"].startswith("application/json")
    assert report_response.headers["content-disposition"] == (
        'attachment; filename="lionsforge-review-queue-comparison-report.json"'
    )

    report = report_response.json()
    assert report["contract_version"] == "1.0"
    assert report["artifact_type"] == (
        "cross_investigation_review_queue_comparison_report"
    )
    assert report["generated_from"] == "verified_snapshot_comparison"
    assert report["comparison"] == comparison.json()
    assert report["comparison"]["added_items"][0]["claim_statement"] == "New claim"
    assert report["comparison"]["reason_count_deltas"] == {
        "missing_validation": 1
    }
    assert report["comparison"]["investigation_count_delta"] == 1
    assert "workflow state" in report["interpretation_notice"]

    reconstructed = _canonical_digest(
        report,
        excluded={"generated_at", "content_sha256"},
    )
    assert report["content_sha256"] == reconstructed
    assert report_response.headers["x-content-sha256"] == reconstructed


def test_report_export_preserves_unchanged_and_empty_deltas(client):
    headers = auth_headers(client, email="report-unchanged@example.com")
    _create_claim(client, headers, "Stable", "Stable claim")
    prior = client.get(SNAPSHOT, headers=headers).json()

    response = client.post(REPORT, headers=headers, json=prior)

    assert response.status_code == 200
    comparison = response.json()["comparison"]
    assert comparison["added_items"] == []
    assert comparison["removed_items"] == []
    assert len(comparison["unchanged_items"]) == 1
    assert comparison["reason_count_deltas"] == {"missing_validation": 0}
    assert comparison["investigation_count_delta"] == 0


def test_report_export_rejects_snapshot_digest_mismatch(client):
    headers = auth_headers(client, email="report-digest@example.com")
    prior = client.get(SNAPSHOT, headers=headers).json()
    prior["content_sha256"] = "0" * 64

    response = client.post(REPORT, headers=headers, json=prior)

    assert response.status_code == 400
    assert "digest" in response.json()["detail"].lower()
    assert "content-disposition" not in response.headers
    assert "x-content-sha256" not in response.headers


def test_report_export_uses_only_current_owner_queue(client):
    first_headers = auth_headers(client, email="report-owner-one@example.com")
    prior = client.get(SNAPSHOT, headers=first_headers).json()

    second_headers = auth_headers(client, email="report-owner-two@example.com")
    _create_claim(client, second_headers, "Other owner", "Other owner claim")

    response = client.post(REPORT, headers=first_headers, json=prior)

    assert response.status_code == 200
    comparison = response.json()["comparison"]
    assert comparison["added_items"] == []
    assert comparison["current_investigation_count"] == 0
