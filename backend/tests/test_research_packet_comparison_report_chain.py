import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = "/api/v1/research-packet-comparison-report-chain/verify"


def canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def packet(content: dict[str, object]) -> dict[str, object]:
    return {"content_sha256": canonical_sha256(content), "content": content}


def comparison_report(
    left: dict[str, object],
    right: dict[str, object],
) -> dict[str, object]:
    left_hash = canonical_sha256(left)
    right_hash = canonical_sha256(right)
    content = {
        "schema_version": "1.0",
        "report_type": "research_packet_comparison",
        "status": "different",
        "left_supplied_sha256": left_hash,
        "left_computed_sha256": left_hash,
        "left_hash_matches": True,
        "right_supplied_sha256": right_hash,
        "right_computed_sha256": right_hash,
        "right_hash_matches": True,
        "left_schema_version": "1.0",
        "right_schema_version": "1.0",
        "supported_schema_versions": ["1.0"],
        "added_count": 0,
        "removed_count": 0,
        "changed_count": 1,
        "differences": [{"path": "title", "kind": "changed"}],
        "detail": "The packet content contains structural differences.",
        "disclaimer": "Structural differences only.",
    }
    return {"report_sha256": canonical_sha256(content), "content": content}


def request_body() -> dict[str, object]:
    left = {"schema_version": "1.0", "title": "Earlier"}
    right = {"schema_version": "1.0", "title": "Later"}
    return {
        "left": packet(left),
        "right": packet(right),
        "report": comparison_report(left, right),
    }


def test_requires_authentication(client: TestClient):
    response = client.post(ENDPOINT, json=request_body())
    assert response.status_code == 401


def test_reports_consistent_integrity_chain(client: TestClient):
    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=request_body(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "consistent"
    assert body["left_packet_hash_matches"] is True
    assert body["right_packet_hash_matches"] is True
    assert body["report_hash_matches"] is True
    assert body["failed_checks"] == []
    assert "does not certify" in body["disclaimer"]


def test_reports_inconsistent_report_status(client: TestClient):
    payload = request_body()
    report = payload["report"]
    assert isinstance(report, dict)
    content = report["content"]
    assert isinstance(content, dict)
    content["status"] = "identical"
    report["report_sha256"] = canonical_sha256(content)

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "inconsistent"
    assert body["report_hash_matches"] is True
    assert "report_status" in body["failed_checks"]


def test_reports_changed_source_packet(client: TestClient):
    payload = request_body()
    left = payload["left"]
    assert isinstance(left, dict)
    content = left["content"]
    assert isinstance(content, dict)
    content["title"] = "Changed after export"

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "inconsistent"
    assert body["left_packet_hash_matches"] is False
    assert "left_packet_hash" in body["failed_checks"]
    assert "report_left_computed_hash" in body["failed_checks"]


def test_reports_unsupported_packet_schema(client: TestClient):
    payload = request_body()
    left = payload["left"]
    assert isinstance(left, dict)
    content = left["content"]
    assert isinstance(content, dict)
    content["schema_version"] = "2.0"
    left["content_sha256"] = canonical_sha256(content)

    response = client.post(
        ENDPOINT,
        headers=auth_headers(client),
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["failed_checks"] == ["supported_schema_and_report_type"]
