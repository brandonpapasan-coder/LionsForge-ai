import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = "/api/v1/research-packet-comparison-report-integrity/verify"


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
        "report_type": "research_packet_comparison",
        "status": "different",
        "differences": [{"path": "title", "kind": "changed"}],
    }


def test_requires_authentication(client: TestClient):
    content = report_content()
    response = client.post(
        ENDPOINT,
        json={"report_sha256": canonical_sha256(content), "content": content},
    )
    assert response.status_code == 401


def test_reports_matching_comparison_report(client: TestClient):
    headers = auth_headers(client)
    content = report_content()
    supplied_hash = canonical_sha256(content)

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"report_sha256": supplied_hash, "content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matching"
    assert body["supplied_sha256"] == supplied_hash
    assert body["computed_sha256"] == supplied_hash
    assert body["schema_version"] == "1.0"
    assert body["report_type"] == "research_packet_comparison"
    assert body["supported_schema_versions"] == ["1.0"]
    assert body["supported_report_types"] == ["research_packet_comparison"]
    assert "does not certify" in body["disclaimer"]


def test_reports_changed_comparison_report(client: TestClient):
    headers = auth_headers(client)
    content = report_content()

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"report_sha256": "0" * 64, "content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "changed"
    assert body["computed_sha256"] == canonical_sha256(content)
    assert body["computed_sha256"] != body["supplied_sha256"]


def test_reports_unsupported_schema_version(client: TestClient):
    headers = auth_headers(client)
    content = report_content() | {"schema_version": "2.0"}

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"report_sha256": canonical_sha256(content), "content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["schema_version"] == "2.0"


def test_reports_unsupported_report_type(client: TestClient):
    headers = auth_headers(client)
    content = report_content() | {"report_type": "other_report"}

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"report_sha256": canonical_sha256(content), "content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["report_type"] == "other_report"


def test_canonical_hash_is_key_order_independent(client: TestClient):
    headers = auth_headers(client)
    first = report_content()
    second = {
        "differences": [{"kind": "changed", "path": "title"}],
        "status": "different",
        "report_type": "research_packet_comparison",
        "schema_version": "1.0",
    }

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"report_sha256": canonical_sha256(first), "content": second},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "matching"
