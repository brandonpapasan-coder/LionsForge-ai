from tests.conftest import auth_headers


def _create_project_and_session(client, headers, suffix: str = "primary") -> tuple[int, int]:
    project_response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={
            "title": f"Evidence project {suffix}",
            "description": "Project used to validate persistent research evidence.",
            "objective": "Verify evidence lifecycle and ownership.",
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    session_response = client.post(
        f"/api/v1/research-projects/{project_id}/sessions",
        headers=headers,
        json={
            "title": f"Evidence session {suffix}",
            "objective": "Collect and review traceable source material.",
        },
    )
    assert session_response.status_code == 201
    return project_id, session_response.json()["id"]


def _create_evidence(client, headers, session_id: int, title: str = "Primary source"):
    return client.post(
        f"/api/v1/research-sessions/{session_id}/evidence",
        headers=headers,
        json={
            "title": title,
            "summary": "A traceable source summary for regression testing.",
            "source_type": "filing",
            "source_reference": "https://example.com/source",
            "tags": ["primary", "verified"],
        },
    )


def test_research_evidence_requires_authentication(client):
    response = client.post(
        "/api/v1/research-sessions/1/evidence",
        json={"title": "Unauthenticated evidence"},
    )
    assert response.status_code == 401


def test_research_evidence_lifecycle_search_and_archive(client):
    headers = auth_headers(client)
    project_id, session_id = _create_project_and_session(client, headers)

    created = _create_evidence(client, headers, session_id)
    assert created.status_code == 201
    payload = created.json()
    evidence_id = payload["id"]
    assert payload["project_id"] == project_id
    assert payload["session_id"] == session_id
    assert payload["source_type"] == "filing"
    assert payload["tags"] == ["primary", "verified"]

    listed = client.get(
        f"/api/v1/research-sessions/{session_id}/evidence?query=traceable",
        headers=headers,
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [evidence_id]

    read = client.get(f"/api/v1/evidence/{evidence_id}", headers=headers)
    assert read.status_code == 200
    assert read.json()["title"] == "Primary source"

    updated = client.patch(
        f"/api/v1/evidence/{evidence_id}",
        headers=headers,
        json={"title": "Reviewed primary source", "tags": ["reviewed"]},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Reviewed primary source"
    assert updated.json()["tags"] == ["reviewed"]

    archived = client.delete(f"/api/v1/evidence/{evidence_id}", headers=headers)
    assert archived.status_code == 204

    active_list = client.get(f"/api/v1/research-sessions/{session_id}/evidence", headers=headers)
    assert active_list.status_code == 200
    assert active_list.json() == []

    archived_list = client.get(
        f"/api/v1/research-sessions/{session_id}/evidence?include_archived=true",
        headers=headers,
    )
    assert archived_list.status_code == 200
    assert archived_list.json()[0]["status"] == "archived"


def test_research_evidence_isolated_between_users(client):
    owner_headers = auth_headers(client, email="owner@example.com")
    _, session_id = _create_project_and_session(client, owner_headers, suffix="owner")
    created = _create_evidence(client, owner_headers, session_id, title="Owner-only source")
    assert created.status_code == 201
    evidence_id = created.json()["id"]

    other_headers = auth_headers(client, email="other@example.com")

    assert client.get(f"/api/v1/evidence/{evidence_id}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/evidence/{evidence_id}",
            headers=other_headers,
            json={"title": "Unauthorized change"},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/evidence/{evidence_id}", headers=other_headers).status_code == 404
    assert (
        client.get(
            f"/api/v1/research-sessions/{session_id}/evidence",
            headers=other_headers,
        ).status_code
        == 404
    )
