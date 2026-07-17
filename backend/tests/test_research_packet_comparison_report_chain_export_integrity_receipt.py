import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = (
    "/api/v1/"
    "research-packet-comparison-report-chain-export-integrity-receipt/export"
)


def canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def report_content() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "report_type": "research_packet_comparison_chain_verification",
        "chain_status": "consistent",
        "left_supplied_sha256": "a" * 64,
        "left_computed_sha256": "a" * 64,
        "left_hash_matches": True,
        "right_supplied_sha256": "b" * 64,
        "right_computed_sha256": "b" * 64,
        "right_hash_matches": True,
        "comparison_report_supplied_sha256": "c" * 64,
        "comparison_report_computed_sha256": "c" * 64,
        "comparison_report_hash_matches": True,
        "left_schema_version": "1.0",
        "right_schema_version": "1.0",
        "comparison_report_schema_version": "1.0",
        "comparison_report_type": "research_packet_comparison",
        "failed_checks": [],
        "detail": "The packets and comparison report form a consistent integrity chain.",
        "disclaimer": "Integrity verification only.",
    }


def request_body() -> dict[str, object]:
    content = report_content()
    return {
        "verification_report_sha256": canonical_sha256(content),
        "content": content,
    }


def test_requires_authentication(client: TestClient):
    response = client.post(ENDPOINT, json=request_body())
    assert response.status_code == 401


def test_exports_deterministic_matching_receipt(client: TestClient):
    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=request_body(),
    )

    assert response.status_code == 200
    body = response.json()
    content = body["content"]
    assert content["schema_version"] == "1.0"
    assert (
        content["report_type"]
        == "research_packet_comparison_chain_verification_integrity_receipt"
    )
    assert content["integrity_status"] == "matching"
    assert content["supplied_sha256"] == content["computed_sha256"]
    assert body["integrity_receipt_sha256"] == canonical_sha256(content)


def test_exports_changed_receipt(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    content["chain_status"] = "inconsistent"

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    receipt = response.json()["content"]
    assert receipt["integrity_status"] == "changed"
    assert receipt["supplied_sha256"] != receipt["computed_sha256"]


def test_key_order_does_not_change_receipt(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    payload["content"] = dict(reversed(list(content.items())))
    headers = auth_headers(client)

    first = client.post(
        ENDPOINT,
        headers=headers,
        json=payload,
    )
    second = client.post(
        ENDPOINT,
        headers=headers,
        json=request_body(),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_exports_unsupported_receipt(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    content["schema_version"] = "2.0"
    payload["verification_report_sha256"] = canonical_sha256(content)

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    receipt = response.json()["content"]
    assert receipt["integrity_status"] == "unsupported"
    assert receipt["source_schema_version"] == "2.0"
