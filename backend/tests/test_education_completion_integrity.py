from tests.conftest import auth_headers


LESSON_URL = "/api/v1/education/lessons/financial-statements-foundations/progress"


def test_general_progress_endpoint_rejects_manual_completion(client):
    headers = auth_headers(client, email="manual-completion@example.com")

    response = client.put(LESSON_URL, headers=headers, json={"status": "completed", "score": 100})

    assert response.status_code == 422
    hub = client.get("/api/v1/education", headers=headers).json()
    assert hub["completed_lessons"] == 0
    assert hub["assessed_lessons"] == 0
    assert hub["recommended_lesson_slug"] == "financial-statements-foundations"


def test_in_progress_preserves_optional_and_remediation_scores(client):
    headers = auth_headers(client, email="in-progress-score@example.com")

    started = client.put(LESSON_URL, headers=headers, json={"status": "in_progress", "score": None})
    assert started.status_code == 200
    assert started.json()["recommended_lesson_slug"] == "financial-statements-foundations"

    remediation = client.put(LESSON_URL, headers=headers, json={"status": "in_progress", "score": 55})
    assert remediation.status_code == 200
    payload = remediation.json()
    assert payload["completed_lessons"] == 0
    assert payload["assessed_lessons"] == 1
    assert payload["recommended_lesson_slug"] == "financial-statements-foundations"
