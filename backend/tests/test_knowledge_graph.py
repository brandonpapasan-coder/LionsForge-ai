from tests.conftest import auth_headers


def create_entity(client, headers, name, entity_type="technology"):
    response = client.post(
        "/api/v1/knowledge-graph/entities",
        headers=headers,
        json={
            "entity_type": entity_type,
            "name": name,
            "description": f"Knowledge entity for {name}",
            "confidence": 0.9,
            "validation_status": "validated",
            "provenance": {"source": "integration-test"},
            "attributes": {"stage": "mvp"},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_relationship(client, headers, source_id, target_id, relationship_type="DEPENDS_ON"):
    response = client.post(
        "/api/v1/knowledge-graph/relationships",
        headers=headers,
        json={
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": relationship_type,
            "confidence": 0.85,
            "validation_status": "validated",
            "provenance": {"source": "integration-test"},
            "attributes": {},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_knowledge_graph_requires_authentication(client):
    response = client.get("/api/v1/knowledge-graph")
    assert response.status_code == 401


def test_create_search_and_connect_entities(client):
    headers = auth_headers(client, email="graph-owner@example.com")
    ai = create_entity(client, headers, "Artificial Intelligence")
    chips = create_entity(client, headers, "Semiconductors", "industry")
    relationship = create_relationship(client, headers, ai["id"], chips["id"])

    graph = client.get("/api/v1/knowledge-graph", headers=headers)
    assert graph.status_code == 200
    assert len(graph.json()["entities"]) == 2
    assert len(graph.json()["relationships"]) == 1

    search = client.get("/api/v1/knowledge-graph/search?q=artificial", headers=headers)
    assert search.status_code == 200
    assert [item["id"] for item in search.json()] == [ai["id"]]

    connected = client.get(
        f"/api/v1/knowledge-graph/entities/{ai['id']}/relationships",
        headers=headers,
    )
    assert connected.status_code == 200
    assert connected.json()[0]["id"] == relationship["id"]


def test_graph_data_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="graph-one@example.com")
    entity = create_entity(client, owner_headers, "Private Research Entity")

    other_headers = auth_headers(client, email="graph-two@example.com")
    graph = client.get("/api/v1/knowledge-graph", headers=other_headers)
    assert graph.status_code == 200
    assert graph.json() == {"entities": [], "relationships": []}

    direct = client.get(
        f"/api/v1/knowledge-graph/entities/{entity['id']}",
        headers=other_headers,
    )
    assert direct.status_code == 404


def test_relationship_rejects_foreign_owned_entity(client):
    owner_headers = auth_headers(client, email="graph-owner-a@example.com")
    source = create_entity(client, owner_headers, "Owned Source")

    other_headers = auth_headers(client, email="graph-owner-b@example.com")
    target = create_entity(client, other_headers, "Foreign Target")

    response = client.post(
        "/api/v1/knowledge-graph/relationships",
        headers=owner_headers,
        json={
            "source_entity_id": source["id"],
            "target_entity_id": target["id"],
            "relationship_type": "REFERENCES",
        },
    )
    assert response.status_code == 404


def test_duplicate_entity_is_rejected(client):
    headers = auth_headers(client, email="graph-duplicate@example.com")
    create_entity(client, headers, "Duplicate Entity")
    response = client.post(
        "/api/v1/knowledge-graph/entities",
        headers=headers,
        json={"entity_type": "technology", "name": "Duplicate Entity"},
    )
    assert response.status_code == 409


def test_update_and_delete_graph_resources(client):
    headers = auth_headers(client, email="graph-lifecycle@example.com")
    source = create_entity(client, headers, "Lifecycle Source")
    target = create_entity(client, headers, "Lifecycle Target")
    relationship = create_relationship(client, headers, source["id"], target["id"], "REFERENCES")

    updated_entity = client.patch(
        f"/api/v1/knowledge-graph/entities/{source['id']}",
        headers=headers,
        json={"name": "Updated Source", "confidence": 0.75},
    )
    assert updated_entity.status_code == 200
    assert updated_entity.json()["name"] == "Updated Source"
    assert updated_entity.json()["confidence"] == 0.75

    updated_relationship = client.patch(
        f"/api/v1/knowledge-graph/relationships/{relationship['id']}",
        headers=headers,
        json={"validation_status": "disputed", "confidence": 0.4},
    )
    assert updated_relationship.status_code == 200
    assert updated_relationship.json()["validation_status"] == "disputed"

    deleted_relationship = client.delete(
        f"/api/v1/knowledge-graph/relationships/{relationship['id']}",
        headers=headers,
    )
    assert deleted_relationship.status_code == 204

    deleted_entity = client.delete(
        f"/api/v1/knowledge-graph/entities/{target['id']}",
        headers=headers,
    )
    assert deleted_entity.status_code == 204

    assert client.get(
        f"/api/v1/knowledge-graph/relationships/{relationship['id']}",
        headers=headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/knowledge-graph/entities/{target['id']}",
        headers=headers,
    ).status_code == 404


def test_bounded_graph_traversal(client):
    headers = auth_headers(client, email="graph-traversal@example.com")
    first = create_entity(client, headers, "First Node")
    second = create_entity(client, headers, "Second Node")
    third = create_entity(client, headers, "Third Node")
    create_relationship(client, headers, first["id"], second["id"], "CONNECTS_TO")
    create_relationship(client, headers, second["id"], third["id"], "CONNECTS_TO")

    depth_one = client.get(
        f"/api/v1/knowledge-graph/entities/{first['id']}/traverse?depth=1",
        headers=headers,
    )
    assert depth_one.status_code == 200
    assert {item["id"] for item in depth_one.json()["entities"]} == {first["id"], second["id"]}
    assert len(depth_one.json()["relationships"]) == 1

    depth_two = client.get(
        f"/api/v1/knowledge-graph/entities/{first['id']}/traverse?depth=2",
        headers=headers,
    )
    assert depth_two.status_code == 200
    assert {item["id"] for item in depth_two.json()["entities"]} == {
        first["id"],
        second["id"],
        third["id"],
    }
    assert len(depth_two.json()["relationships"]) == 2
