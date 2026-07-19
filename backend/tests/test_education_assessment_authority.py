from tests.conftest import auth_headers


LESSON_URL = "/api/v1/education/lessons/financial-statements-foundations/progress"


def test_progress_endpoint_rejects_manual_completion_and_assessment_unlocks_next_lesson(client):
    headers = auth_headers(client, email="assessment-authority@example.com")

    manual_completion = client.put(
        LESSON_URL,
        headers=headers,
        json={"status": "completed", "score": 100},
    )
    assert manual_completion.status_code == 422

    assessment = client.get("/api/v1/education/assessment", headers=headers)
    assert assessment.status_code == 200
    question = assessment.json()["question"]

    submission = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={"question_id": question["id"], "selected_option": 0},
    )
    assert submission.status_code == 200
    payload = submission.json()
    assert payload["passed"] is True
    assert payload["education_hub"]["completed_lessons"] == 1
    assert payload["education_hub"]["recommended_lesson_slug"] == "valuation-and-cash-flow"
