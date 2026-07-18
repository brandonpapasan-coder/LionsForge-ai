from tests.conftest import auth_headers


def create_project(client, headers, title="Personal memory lifecycle"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Verify user-controlled memory lifecycle"},
    )
    assert response.status_code == 201
    return response.json()


def create_memory(client, headers, project_id):
    return client.post(
        "/api/v1/knowledge-memory/user-authored",
        headers=headers,
        json={
            "project_id": project_id,
            "statement": "I prefer primary sources and explicit uncertainty.",
            "summary": "Prefer primary sources with explicit uncertainty.",
            "category": "research_preference",
            "confidence": 0.9,
            "source_evidence_ids": [],
            "provenance": {"basis": "explicit_user_preference"},
        },
    )


def context(client, headers, project_id):
    return client.post(
        "/api/v1/personal-intelligence/context",
        headers=headers,
        json={
            "audience": "research_assistant",
            "project_id": project_id,
            "include_provisional": True,
        },
    )


def test_user_authored_memory_lifecycle_updates_context_immediately(client):
    headers = auth_headers(client, email="personal-lifecycle@example.com")
    project = create_project(client, headers)

    first = create_memory(client, headers, project["id"])
    duplicate = create_memory(client, headers, project["id"])
    assert first.status_code == 201
    assert duplicate.status_code == 201
    memory = first.json()
    assert duplicate.json()["id"] == memory["id"]
    assert memory["mission_id"] is None
    assert memory["snapshot_id"] is None
    assert memory["status"] == "provisional"
    assert len(memory["revisions"]) == 1

    visible = context(client, headers, project["id"])
    assert visible.status_code == 200
    assert memory["id"] in visible.json()["trace_memory_ids"]

    revised = client.patch(
        f"/api/v1/knowledge-memory/{memory['id']}",
        headers=headers,
        json={"summary": "Prefer primary sources and clearly label uncertainty."},
    )
    assert revised.status_code == 200
    assert revised.json()["revision_number"] == 2
    assert len(revised.json()["revisions"]) == 2

    archived = client.post(
        f"/api/v1/knowledge-memory/{memory['id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert memory["id"] not in context(client, headers, project["id"]).json()[
        "trace_memory_ids"
    ]

    restored = client.post(
        f"/api/v1/knowledge-memory/{memory['id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "provisional"
    assert memory["id"] in context(client, headers, project["id"]).json()[
        "trace_memory_ids"
    ]

    deleted = client.delete(
        f"/api/v1/knowledge-memory/{memory['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/api/v1/knowledge-memory/{memory['id']}", headers=headers
    ).status_code == 404
    assert memory["id"] not in context(client, headers, project["id"]).json()[
        "trace_memory_ids"
    ]


def test_recovering_prior_version_creates_new_revision_and_preserves_history(client):
    headers = auth_headers(client, email="personal-recovery@example.com")
    project = create_project(client, headers, "Version recovery")
    created = create_memory(client, headers, project["id"])
    assert created.status_code == 201
    original = created.json()
    original_revision_id = original["revisions"][0]["id"]

    revised = client.patch(
        f"/api/v1/knowledge-memory/{original['id']}",
        headers=headers,
        json={
            "statement": "I prefer peer-reviewed secondary sources.",
            "summary": "Prefer peer-reviewed secondary sources.",
            "category": "research_context",
            "confidence": 0.6,
        },
    )
    assert revised.status_code == 200
    assert revised.json()["revision_number"] == 2

    recovered = client.post(
        f"/api/v1/knowledge-memory/{original['id']}/recover/{original_revision_id}",
        headers=headers,
    )
    assert recovered.status_code == 200
    payload = recovered.json()
    assert payload["revision_number"] == 3
    assert payload["statement"] == original["statement"]
    assert payload["summary"] == original["summary"]
    assert payload["category"] == original["category"]
    assert payload["confidence"] == original["confidence"]
    assert payload["status"] == original["status"]
    assert len(payload["revisions"]) == 3
    assert [item["revision_number"] for item in payload["revisions"]] == [1, 2, 3]


def test_recovery_rejects_foreign_revision_and_preserves_owner_isolation(client):
    owner_headers = auth_headers(client, email="recovery-owner@example.com")
    other_headers = auth_headers(client, email="recovery-other@example.com")
    owner_project = create_project(client, owner_headers, "Recovery owner")
    other_project = create_project(client, other_headers, "Recovery other")
    owner_memory = create_memory(client, owner_headers, owner_project["id"]).json()
    other_memory = create_memory(client, other_headers, other_project["id"]).json()

    foreign_revision_id = other_memory["revisions"][0]["id"]
    assert client.post(
        f"/api/v1/knowledge-memory/{owner_memory['id']}/recover/{foreign_revision_id}",
        headers=owner_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/knowledge-memory/{owner_memory['id']}/recover/{owner_memory['revisions'][0]['id']}",
        headers=other_headers,
    ).status_code == 404


def test_user_authored_memory_operations_enforce_owner_isolation(client):
    owner_headers = auth_headers(client, email="personal-owner@example.com")
    other_headers = auth_headers(client, email="personal-other@example.com")
    project = create_project(client, owner_headers, "Private personal memory")
    created = create_memory(client, owner_headers, project["id"])
    assert created.status_code == 201
    memory_id = created.json()["id"]

    assert client.get(
        f"/api/v1/knowledge-memory/{memory_id}", headers=other_headers
    ).status_code == 404
    assert client.patch(
        f"/api/v1/knowledge-memory/{memory_id}",
        headers=other_headers,
        json={"summary": "Unauthorized change"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/knowledge-memory/{memory_id}/archive", headers=other_headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/knowledge-memory/{memory_id}/restore", headers=other_headers
    ).status_code == 404
    assert client.delete(
        f"/api/v1/knowledge-memory/{memory_id}", headers=other_headers
    ).status_code == 404

    denied_context = context(client, other_headers, project["id"])
    assert denied_context.status_code == 200
    assert memory_id not in denied_context.json()["trace_memory_ids"]

    owner_read = client.get(
        f"/api/v1/knowledge-memory/{memory_id}", headers=owner_headers
    )
    assert owner_read.status_code == 200
