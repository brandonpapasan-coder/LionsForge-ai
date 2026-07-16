import hashlib
import json

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

ENDPOINT = "/api/v1/research-packet-comparison/compare"


def canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def packet(content: dict[str, object], supplied_hash: str | None = None) -> dict[str, object]:
    return {"content_sha256": supplied_hash or canonical_sha256(content), "content": content}


def test_requires_authentication(client: TestClient):
    content = {"schema_version": "1.0"}
    response = client.post(ENDPOINT, json={"left": packet(content), "right": packet(content)})
    assert response.status_code == 401


def test_reports_identical_packets(client: TestClient):
    headers = auth_headers(client)
    left = {"schema_version": "1.0", "project_id": 7, "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "project_id": 7, "schema_version": "1.0"}
    response = client.post(ENDPOINT, headers=headers, json={"left": packet(left), "right": packet(right)})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "identical"
    assert body["differences"] == []
    assert body["left_hash_matches"] is True
    assert body["right_hash_matches"] is True


def test_reports_deterministic_added_removed_and_changed_paths(client: TestClient):
    headers = auth_headers(client)
    left = {"schema_version": "1.0", "title": "Old", "items": [{"id": 1}, {"id": 2}], "removed": True}
    right = {"schema_version": "1.0", "title": "New", "items": [{"id": 1}, {"id": 3}, {"id": 4}], "added": True}
    response = client.post(ENDPOINT, headers=headers, json={"left": packet(left), "right": packet(right)})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "different"
    assert body["differences"] == [
        {"path": "added", "kind": "added"},
        {"path": "items[1].id", "kind": "changed"},
        {"path": "items[2]", "kind": "added"},
        {"path": "removed", "kind": "removed"},
        {"path": "title", "kind": "changed"},
    ]
    assert body["added_count"] == 2
    assert body["removed_count"] == 1
    assert body["changed_count"] == 2


def test_reports_hash_mismatch_without_blocking_comparison(client: TestClient):
    headers = auth_headers(client)
    left = {"schema_version": "1.0", "value": 1}
    right = {"schema_version": "1.0", "value": 2}
    response = client.post(
        ENDPOINT,
        headers=headers,
        json={"left": packet(left, "0" * 64), "right": packet(right)},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "different"
    assert body["left_hash_matches"] is False
    assert body["right_hash_matches"] is True


def test_reports_unsupported_schema(client: TestClient):
    headers = auth_headers(client)
    left = {"schema_version": "1.0"}
    right = {"schema_version": "2.0"}
    response = client.post(ENDPOINT, headers=headers, json={"left": packet(left), "right": packet(right)})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "unsupported"
    assert body["right_schema_version"] == "2.0"
    assert body["differences"] == []
