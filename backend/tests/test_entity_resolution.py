from tests.conftest import auth_headers


def create_entity(client, headers, name, entity_type="organization"):
    response = client.post(
        "/api/v1/knowledge-graph/entities",
        headers=headers,
        json={"entity_type": entity_type, "name": name},
    )
    assert response.status_code == 201
    return response.json()


def test_alias_search_and_duplicate_suggestions(client):
    headers = auth_headers(client, email="resolution@example.com")
    canonical = create_entity(client, headers, "Microsoft Corporation")
    duplicate = create_entity(client, headers, "Microsoft Corp")

    alias = client.post(
        f"/api/v1/knowledge-graph/entities/{canonical['id']}/aliases",
        headers=headers,
        json={"alias": "MSFT", "alias_type": "ticker", "confidence": 0.99},
    )
    assert alias.status_code == 201

    search = client.get("/api/v1/knowledge-graph/aliases/search?q=MSFT", headers=headers)
    assert search.status_code == 200
    assert search.json()[0]["id"] == canonical["id"]

    suggestions = client.get(
        f"/api/v1/knowledge-graph/entities/{canonical['id']}/duplicates",
        headers=headers,
    )
    assert suggestions.status_code == 200
    match = next(item for item in suggestions.json() if item["entity"]["id"] == duplicate["id"])
    assert match["score"] == 1.0


def test_merge_moves_relationship_and_preserves_alias(client):
    headers = auth_headers(client, email="merge-resolution@example.com")
    canonical = create_entity(client, headers, "Microsoft Corporation")
    duplicate = create_entity(client, headers, "Microsoft Corp")
    partner = create_entity(client, headers, "OpenAI Group")

    relationship = client.post(
        "/api/v1/knowledge-graph/relationships",
        headers=headers,
        json={
            "source_entity_id": duplicate["id"],
            "target_entity_id": partner["id"],
            "relationship_type": "PARTNERS_WITH",
        },
    )
    assert relationship.status_code == 201

    merged = client.post(
        f"/api/v1/knowledge-graph/entities/{canonical['id']}/merge",
        headers=headers,
        json={"duplicate_entity_id": duplicate["id"], "reason": "same organization"},
    )
    assert merged.status_code == 200
    assert merged.json()["relationships_moved"] == 1
    assert merged.json()["audit_id"] > 0

    missing = client.get(
        f"/api/v1/knowledge-graph/entities/{duplicate['id']}",
        headers=headers,
    )
    assert missing.status_code == 404

    alias_search = client.get(
        "/api/v1/knowledge-graph/aliases/search?q=Microsoft%20Corp",
        headers=headers,
    )
    assert alias_search.status_code == 200
    assert alias_search.json()[0]["id"] == canonical["id"]
