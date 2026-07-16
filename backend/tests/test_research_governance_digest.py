from tests.conftest import auth_headers


def create_project(client, headers, title="Digest project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Review governance digest"},
    )
    assert response.status_code == 201
    return response.json()


def test_digest_preferences_preview_generation_and_history(client):
    headers = auth_headers(client, email="digest-owner@example.com")
    project = create_project(client, headers)
    preference = client.put(
        "/api/v1/research-governance-digest/preferences",
        headers=headers,
        json={
            "project_ids": [project["id"]],
            "impact_levels": ["high_attention", "review_required"],
            "window_days": 30,
            "cadence": "weekly",
        },
    )
    assert preference.status_code == 200
    assert preference.json()["project_ids"] == [project["id"]]

    as_of = "2026-07-16T12:00:00"
    first = client.get(
        f"/api/v1/research-governance-digest/preview?as_of={as_of}", headers=headers
    )
    second = client.get(
        f"/api/v1/research-governance-digest/preview?as_of={as_of}", headers=headers
    )
    assert first.status_code == 200
    assert first.json()["content_sha256"] == second.json()["content_sha256"]
    assert first.json()["items"] == []

    generated = client.post(
        f"/api/v1/research-governance-digest/generate?as_of={as_of}", headers=headers
    )
    assert generated.status_code == 200
    history = client.get("/api/v1/research-governance-digest/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["snapshots"][0]["content_sha256"] == generated.json()["content_sha256"]
    assert history.json()["snapshots"][0]["item_count"] == 0


def test_digest_rejects_foreign_projects_and_unauthenticated_access(client):
    owner = auth_headers(client, email="digest-project-owner@example.com")
    other = auth_headers(client, email="digest-other@example.com")
    project = create_project(client, owner, title="Private digest project")
    denied = client.put(
        "/api/v1/research-governance-digest/preferences",
        headers=other,
        json={
            "project_ids": [project["id"]],
            "impact_levels": ["high_attention"],
            "window_days": 30,
            "cadence": "weekly",
        },
    )
    assert denied.status_code == 404
    unauthenticated = client.get("/api/v1/research-governance-digest/preview")
    assert unauthenticated.status_code == 401
