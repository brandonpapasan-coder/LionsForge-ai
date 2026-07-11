from tests.conftest import auth_headers


def test_education_hub_requires_authentication(client):
    response = client.get("/api/v1/education")
    assert response.status_code == 401


def test_education_hub_returns_catalog_and_progress(client):
    headers = auth_headers(client)
    initial = client.get("/api/v1/education", headers=headers)
    assert initial.status_code == 200
    payload = initial.json()
    assert payload["total_lessons"] == 4
    assert payload["completed_lessons"] == 0
    assert payload["completion_percent"] == 0

    updated = client.put(
        "/api/v1/education/lessons/financial-statements-foundations/progress",
        headers=headers,
        json={"status": "completed", "score": 90},
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["completed_lessons"] == 1
    assert payload["completion_percent"] == 25
    lesson = next(item for item in payload["lessons"] if item["slug"] == "financial-statements-foundations")
    assert lesson["status"] == "completed"
    assert lesson["score"] == 90
    assert lesson["completed_at"] is not None


def test_education_progress_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="learner-one@example.com")
    client.put(
        "/api/v1/education/lessons/evidence-quality-and-bias/progress",
        headers=owner_headers,
        json={"status": "completed", "score": 100},
    )

    other_headers = auth_headers(client, email="learner-two@example.com")
    response = client.get("/api/v1/education", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["completed_lessons"] == 0


def test_unknown_lesson_is_rejected(client):
    headers = auth_headers(client)
    response = client.put(
        "/api/v1/education/lessons/not-a-lesson/progress",
        headers=headers,
        json={"status": "completed", "score": 80},
    )
    assert response.status_code == 404
