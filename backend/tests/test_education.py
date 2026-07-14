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
    assert payload["assessed_lessons"] == 0
    assert payload["completion_percent"] == 0
    assert payload["average_score"] is None
    assert payload["mastery_percent"] == 0
    assert payload["proficiency_band"] == "foundation"
    assert payload["recommended_lesson_slug"] == "financial-statements-foundations"
    assert payload["recommendation_reason"] == "Continue the curriculum with the next unfinished lesson."

    updated = client.put(
        "/api/v1/education/lessons/financial-statements-foundations/progress",
        headers=headers,
        json={"status": "completed", "score": 90},
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["completed_lessons"] == 1
    assert payload["assessed_lessons"] == 1
    assert payload["completion_percent"] == 25
    assert payload["average_score"] == 90
    assert payload["mastery_percent"] == 64
    assert payload["proficiency_band"] == "proficient"
    assert payload["recommended_lesson_slug"] == "valuation-and-cash-flow"
    assert payload["recommendation_reason"] == "Continue the curriculum with the next unfinished lesson."
    lesson = next(item for item in payload["lessons"] if item["slug"] == "financial-statements-foundations")
    assert lesson["status"] == "completed"
    assert lesson["score"] == 90
    assert lesson["completed_at"] is not None

    competency = next(
        item for item in payload["competencies"] if item["competency"] == lesson["competency"]
    )
    assert competency["assessed_lessons"] == 1
    assert competency["average_score"] == 90
    assert competency["mastery_percent"] == 94
    assert competency["proficiency_band"] == "expert"


def test_low_score_prioritizes_unfinished_remediation(client):
    headers = auth_headers(client)
    client.put(
        "/api/v1/education/lessons/financial-statements-foundations/progress",
        headers=headers,
        json={"status": "completed", "score": 95},
    )
    client.put(
        "/api/v1/education/lessons/valuation-and-cash-flow/progress",
        headers=headers,
        json={"status": "in_progress", "score": 55},
    )
    client.put(
        "/api/v1/education/lessons/evidence-quality-and-bias/progress",
        headers=headers,
        json={"status": "in_progress", "score": 65},
    )

    response = client.get("/api/v1/education", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_lesson_slug"] == "valuation-and-cash-flow"
    assert payload["recommendation_reason"] == (
        "Strengthen valuation: your 55% assessment average is below the 70% remediation threshold."
    )


def test_completed_path_has_no_recommendation(client):
    headers = auth_headers(client)
    for slug in (
        "financial-statements-foundations",
        "valuation-and-cash-flow",
        "evidence-quality-and-bias",
        "research-thesis-construction",
    ):
        response = client.put(
            f"/api/v1/education/lessons/{slug}/progress",
            headers=headers,
            json={"status": "completed", "score": 85},
        )
        assert response.status_code == 200

    payload = response.json()
    assert payload["recommended_lesson_slug"] is None
    assert payload["recommendation_reason"] == "All current lessons are complete."


def test_education_progress_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="learner-one@example.com")
    client.put(
        "/api/v1/education/lessons/evidence-quality-and-bias/progress",
        headers=owner_headers,
        json={"status": "in_progress", "score": 40},
    )
    owner_payload = client.get("/api/v1/education", headers=owner_headers).json()
    assert owner_payload["recommended_lesson_slug"] == "evidence-quality-and-bias"

    other_headers = auth_headers(client, email="learner-two@example.com")
    response = client.get("/api/v1/education", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["completed_lessons"] == 0
    assert response.json()["assessed_lessons"] == 0
    assert response.json()["recommended_lesson_slug"] == "financial-statements-foundations"


def test_unknown_lesson_is_rejected(client):
    headers = auth_headers(client)
    response = client.put(
        "/api/v1/education/lessons/not-a-lesson/progress",
        headers=headers,
        json={"status": "completed", "score": 80},
    )
    assert response.status_code == 404
