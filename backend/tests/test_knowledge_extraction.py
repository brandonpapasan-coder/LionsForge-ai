from tests.conftest import auth_headers


SAMPLE_CONTENT = (
    "NVIDIA Corporation (NVDA) supplies Microsoft Corporation with artificial intelligence infrastructure. "
    "Microsoft Corporation partners with OpenAI Group on cloud computing research."
)


def test_extraction_requires_authentication(client):
    response = client.post(
        "/api/v1/knowledge-graph/extract",
        json={"content": SAMPLE_CONTENT},
    )
    assert response.status_code == 401


def test_extraction_preview_returns_candidates_without_persisting(client):
    headers = auth_headers(client, email="extraction-preview@example.com")
    response = client.post(
        "/api/v1/knowledge-graph/extract",
        headers=headers,
        json={
            "content": SAMPLE_CONTENT,
            "source_title": "Sample research note",
            "source_url": "https://example.com/research",
            "persist": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    names = {item["name"] for item in body["entities"]}
    assert "NVIDIA Corporation" in names
    assert "Microsoft Corporation" in names
    assert "Artificial Intelligence" in names
    assert body["persisted_entities"] == []
    assert body["persisted_relationships"] == []

    graph = client.get("/api/v1/knowledge-graph", headers=headers)
    assert graph.status_code == 200
    assert graph.json() == {"entities": [], "relationships": []}


def test_extraction_can_persist_unverified_graph_with_provenance(client):
    headers = auth_headers(client, email="extraction-persist@example.com")
    response = client.post(
        "/api/v1/knowledge-graph/extract",
        headers=headers,
        json={
            "content": SAMPLE_CONTENT,
            "source_title": "Sample research note",
            "source_url": "https://example.com/research",
            "persist": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["persisted_entities"]) >= 3
    assert all(item["validation_status"] == "unverified" for item in body["persisted_entities"])
    assert any(item["relationship_type"] == "SUPPLIES" for item in body["persisted_relationships"])

    nvidia = next(item for item in body["persisted_entities"] if item["name"] == "NVIDIA Corporation")
    assert nvidia["provenance"]["source_title"] == "Sample research note"
    assert nvidia["provenance"]["source_url"] == "https://example.com/research"

    graph = client.get("/api/v1/knowledge-graph", headers=headers)
    assert graph.status_code == 200
    assert len(graph.json()["entities"]) == len(body["persisted_entities"])


def test_repeated_persistence_is_idempotent(client):
    headers = auth_headers(client, email="extraction-idempotent@example.com")
    payload = {"content": SAMPLE_CONTENT, "persist": True}
    first = client.post("/api/v1/knowledge-graph/extract", headers=headers, json=payload)
    second = client.post("/api/v1/knowledge-graph/extract", headers=headers, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    graph = client.get("/api/v1/knowledge-graph", headers=headers)
    assert graph.status_code == 200
    names = [item["name"] for item in graph.json()["entities"]]
    assert len(names) == len(set(names))
