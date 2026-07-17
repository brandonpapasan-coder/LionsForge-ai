import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = (
    "/api/v1/"
    "research-packet-comparison-report-chain-export-integrity-receipt-check/verify"
)


def canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def receipt_content() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "report_type": (
            "research_packet_comparison_chain_verification_integrity_receipt"
        ),
        "integrity_status": "matching",
        "supplied_sha256": "a" * 64,
        "computed_sha256": "a" * 64,
        "source_schema_version": "1.0",
        "source_report_type": "research_packet_comparison_chain_verification",
        "detail": "The report content matches the supplied SHA-256 value.",
        "disclaimer": "Integrity verification only.",
    }


def request_body() -> dict[str, object]:
    content = receipt_content()
    return {
        "integrity_receipt_sha256": canonical_sha256(content),
        "content": content,
    }


def test_requires_authentication(client: TestClient):
    response = client.post(ENDPOINT, json=request_body())
    assert response.status_code == 401


def test_verifies_matching_receipt(client: TestClient):
    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=request_body(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matching"
    assert body["supplied_sha256"] == body["computed_sha256"]
    assert body["schema_version"] == "1.0"


def test_detects_changed_receipt(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    content["integrity_status"] = "changed"

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "changed"
    assert body["supplied_sha256"] != body["computed_sha256"]


def test_key_order_does_not_change_hash(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    payload["content"] = dict(reversed(list(content.items())))

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "matching"


def test_rejects_unsupported_receipt_type(client: TestClient):
    payload = request_body()
    content = payload["content"]
    assert isinstance(content, dict)
    content["report_type"] = "unknown_receipt"
    payload["integrity_receipt_sha256"] = canonical_sha256(content)

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["report_type"] == "unknown_receipt"
