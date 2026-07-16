import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = "/api/v1/research-packet-integrity/verify"


def canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_requires_authentication(client: TestClient):
    response = client.post(ENDPOINT, json={"content_sha256": "a" * 64, "content": {"schema_version": "1.0"}})

    assert response.status_code == 401


def test_reports_matching_packet(client: TestClient):
    headers = auth_headers(client)
    content = {"schema_version": "1.0", "project_id": 7, "nested": {"claim": "Owner-authored"}}
    supplied_hash = canonical_sha256(content)

    response = client.post(ENDPOINT, headers=headers, json={"content_sha256": supplied_hash, "content": content})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "matching"
    assert body["supplied_sha256"] == supplied_hash
    assert body["computed_sha256"] == supplied_hash
    assert body["schema_version"] == "1.0"
    assert body["supported_schema_versions"] == ["1.0"]
    assert "does not certify" in body["disclaimer"]


def test_reports_changed_packet(client: TestClient):
    headers = auth_headers(client)
    content = {"schema_version": "1.0", "project_id": 7, "conclusion": "Changed text"}

    response = client.post(ENDPOINT, headers=headers, json={"content_sha256": "0" * 64, "content": content})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "changed"
    assert body["computed_sha256"] == canonical_sha256(content)
    assert body["computed_sha256"] != body["supplied_sha256"]


def test_reports_unsupported_schema_version(client: TestClient):
    headers = auth_headers(client)
    content = {"schema_version": "2.0", "project_id": 7}

    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"content_sha256": canonical_sha256(content), "content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["schema_version"] == "2.0"
    assert body["supported_schema_versions"] == ["1.0"]


def test_canonical_hash_is_key_order_independent(client: TestClient):
    headers = auth_headers(client)
    first = {"schema_version": "1.0", "project_id": 7, "content": {"b": 2, "a": 1}}
    second = {"content": {"a": 1, "b": 2}, "project_id": 7, "schema_version": "1.0"}
    supplied_hash = canonical_sha256(first)

    response = client.post(ENDPOINT, headers=headers, json={"content_sha256": supplied_hash, "content": second})

    assert response.status_code == 200
    assert response.json()["status"] == "matching"
