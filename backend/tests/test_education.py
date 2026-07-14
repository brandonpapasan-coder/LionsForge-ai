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
    assert (
        payload["recommendation_reason"]
        == "Continue the curriculum with the next available foundation lesson."
    )

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
    assert (
        payload["recommendation_reason"]
        == "Continue with Valuation and Cash Flow; its prerequisite lessons are complete."
    )
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
        "Strengthen valuation: the latest 55% assessment score is below the 70% mastery threshold."
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


def test_adaptive_assessment_requires_authentication(client):
    assert client.get("/api/v1/education/assessment").status_code == 401
    assert client.post(
        "/api/v1/education/assessment",
        json={"question_id": "fs-foundation-1", "selected_option": 1},
    ).status_code == 401


def test_adaptive_assessment_starts_at_foundation_and_explains_difficulty(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/education/assessment", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["lesson_slug"] == "financial-statements-foundations"
    assert payload["competency"] == "financial-statements"
    assert payload["difficulty"] == "foundation"
    assert payload["difficulty_reason"] == "Foundation difficulty selected because mastery is 0%."
    assert payload["question"]["id"] == "fs-foundation-1"
    assert "correct_option" not in payload["question"]
    assert payload["question"]["objective"]


def test_correct_assessment_updates_progress_and_next_recommendation(client):
    headers = auth_headers(client)
    assessment = client.get("/api/v1/education/assessment", headers=headers).json()
    response = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={"question_id": assessment["question"]["id"], "selected_option": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 100
    assert payload["passed"] is True
    assert payload["learning_objective"] == assessment["question"]["objective"]
    assert payload["education_hub"]["completed_lessons"] == 1
    assert payload["education_hub"]["recommended_lesson_slug"] == "valuation-and-cash-flow"


def test_incorrect_assessment_keeps_lesson_in_remediation(client):
    headers = auth_headers(client)
    assessment = client.get("/api/v1/education/assessment", headers=headers).json()
    response = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={"question_id": assessment["question"]["id"], "selected_option": 0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 0
    assert payload["passed"] is False
    assert payload["education_hub"]["recommended_lesson_slug"] == "financial-statements-foundations"
    assert "below the 70% mastery threshold" in payload["education_hub"]["recommendation_reason"]


def test_assessment_difficulty_advances_with_mastery(client):
    headers = auth_headers(client)
    client.put(
        "/api/v1/education/lessons/financial-statements-foundations/progress",
        headers=headers,
        json={"status": "completed", "score": 95},
    )
    client.put(
        "/api/v1/education/lessons/valuation-and-cash-flow/progress",
        headers=headers,
        json={"status": "in_progress", "score": 80},
    )
    response = client.get("/api/v1/education/assessment", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["lesson_slug"] == "valuation-and-cash-flow"
    assert payload["difficulty"] == "intermediate"
    assert payload["question"]["id"] == "valuation-intermediate-1"


def test_stale_or_invalid_assessment_submission_is_rejected(client):
    headers = auth_headers(client)
    stale = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={"question_id": "valuation-foundation-1", "selected_option": 0},
    )
    assert stale.status_code == 409

    assessment = client.get("/api/v1/education/assessment", headers=headers).json()
    invalid_option = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={"question_id": assessment["question"]["id"], "selected_option": 99},
    )
    assert invalid_option.status_code == 422


def test_assessment_progress_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="assessment-owner@example.com")
    assessment = client.get("/api/v1/education/assessment", headers=owner_headers).json()
    client.post(
        "/api/v1/education/assessment",
        headers=owner_headers,
        json={"question_id": assessment["question"]["id"], "selected_option": 1},
    )

    other_headers = auth_headers(client, email="assessment-other@example.com")
    other = client.get("/api/v1/education", headers=other_headers).json()
    assert other["completed_lessons"] == 0
    assert other["assessed_lessons"] == 0


def test_completed_path_rejects_new_assessment(client):
    headers = auth_headers(client)
    for slug in (
        "financial-statements-foundations",
        "valuation-and-cash-flow",
        "evidence-quality-and-bias",
        "research-thesis-construction",
    ):
        client.put(
            f"/api/v1/education/lessons/{slug}/progress",
            headers=headers,
            json={"status": "completed", "score": 85},
        )
    response = client.get("/api/v1/education/assessment", headers=headers)
    assert response.status_code == 409


def test_unknown_lesson_is_rejected(client):
    headers = auth_headers(client)
    response = client.put(
        "/api/v1/education/lessons/not-a-lesson/progress",
        headers=headers,
        json={"status": "completed", "score": 80},
    )
    assert response.status_code == 404
