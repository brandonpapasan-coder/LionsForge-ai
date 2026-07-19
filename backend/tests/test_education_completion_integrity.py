from tests.conftest import auth_headers


LESSON_URL = "/api/v1/education/lessons/financial-statements-foundations/progress"


def test_completed_lesson_requires_score(client):
    headers = auth_headers(client, email="completion-missing-score@example.com")

    response = client.put(LESSON_URL, headers=headers, json={"status": "completed", "score": None})

    assert response.status_code == 422
    hub = client.get("/api/v1/education", headers=headers).json()
    assert hub["completed_lessons"] == 0
    assert hub["recommended_lesson_slug"] == "financial-statements-foundations"


def test_completed_lesson_requires_passing_score(client):
    headers = auth_headers(client, email="completion-failing-score@example.com")

    response = client.put(LESSON_URL, headers=headers, json={"status": "completed", "score": 69})

    assert response.status_code == 422
    hub = client.get("/api/v1/education", headers=headers).json()
    assert hub["completed_lessons"] == 0
    assert hub["assessed_lessons"] == 0


def test_in_progress_allows_remediation_score_and_passing_completion(client):
    headers = auth_headers(client, email="completion-passing-score@example.com")

    remediation = client.put(LESSON_URL, headers=headers, json={"status": "in_progress", "score": 55})
    assert remediation.status_code == 200
    assert remediation.json()["recommended_lesson_slug"] == "financial-statements-foundations"

    completed = client.put(LESSON_URL, headers=headers, json={"status": "completed", "score": 70})
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["completed_lessons"] == 1
    assert payload["recommended_lesson_slug"] == "valuation-and-cash-flow"
