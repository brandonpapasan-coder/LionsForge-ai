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


def test_knowledge_graph_requires_authentication(client):
    response = client.get("/api/v1/knowledge-graph")
    assert response.status_code == 401


def test_create_search_and_connect_entities(client):
    headers = auth_headers(client, email="graph-owner@example.com")
    ai = create_entity(client, headers, "Artificial Intelligence")
    chips = create_entity(client, headers, "Semiconductors", "industry")

    relationship = client.post(
        "/api/v1/knowledge-graph/relationships",
        headers=headers,
        json={
            "source_entity_id": ai["id"],
            "target_entity_id": chips["id"],
            "relationship_type": "DEPENDS_ON",
            "description": "AI infrastructure depends on semiconductor capacity.",
            "confidence": 0.85,
            "validation_status": "validated",
            "provenance": {"source": "integration-test"},
            "attributes": {},
        },
    )
    assert relationship.status_code == 201

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
    assert connected.json()[0]["target_entity_id"] == chips["id"]


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
