from app.services.assessments import ASSESSMENT_BANK
from tests.conftest import auth_headers


HISTORY_URL = "/api/v1/education/assessment/history"
ASSESSMENT_URL = "/api/v1/education/assessment"


def submit_current_assessment(client, headers, *, correct: bool):
    assessment_response = client.get(ASSESSMENT_URL, headers=headers)
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    question = ASSESSMENT_BANK[assessment["lesson_slug"]][assessment["difficulty"]]
    selected_option = question["correct_option"]
    if not correct:
        selected_option = next(index for index in range(len(question["options"])) if index != question["correct_option"])
    response = client.post(
        ASSESSMENT_URL,
        headers=headers,
        json={"question_id": question["id"], "selected_option": selected_option},
    )
    assert response.status_code == 200
    return response.json(), question, selected_option


def test_assessment_history_requires_authentication(client):
    response = client.get(HISTORY_URL)
    assert response.status_code == 401


def test_failed_and_passing_attempts_are_retained_without_answer_key(client):
    headers = auth_headers(client, email="attempt-history@example.com")

    failed, failed_question, failed_option = submit_current_assessment(client, headers, correct=False)
    assert failed["passed"] is False
    passed, passed_question, passed_option = submit_current_assessment(client, headers, correct=True)
    assert passed["passed"] is True

    response = client.get(HISTORY_URL, headers=headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2
    assert [attempt["passed"] for attempt in history] == [True, False]
    assert history[0]["question_id"] == passed_question["id"]
    assert history[0]["selected_option"] == passed_option
    assert history[0]["score"] == 100
    assert history[1]["question_id"] == failed_question["id"]
    assert history[1]["selected_option"] == failed_option
    assert history[1]["score"] == 0
    assert all("correct_option" not in attempt for attempt in history)
    assert all(attempt["created_at"] for attempt in history)


def test_stale_and_out_of_range_submissions_do_not_create_attempts(client):
    headers = auth_headers(client, email="invalid-attempts@example.com")

    stale = client.post(
        ASSESSMENT_URL,
        headers=headers,
        json={"question_id": "valuation-foundation-1", "selected_option": 0},
    )
    assert stale.status_code == 409

    assessment = client.get(ASSESSMENT_URL, headers=headers).json()
    invalid = client.post(
        ASSESSMENT_URL,
        headers=headers,
        json={"question_id": assessment["question"]["id"], "selected_option": 99},
    )
    assert invalid.status_code == 422

    history = client.get(HISTORY_URL, headers=headers)
    assert history.status_code == 200
    assert history.json() == []


def test_assessment_history_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="attempt-owner@example.com")
    submit_current_assessment(client, owner_headers, correct=False)

    other_headers = auth_headers(client, email="attempt-other@example.com")
    other_history = client.get(HISTORY_URL, headers=other_headers)
    assert other_history.status_code == 200
    assert other_history.json() == []

    owner_history = client.get(HISTORY_URL, headers=owner_headers)
    assert owner_history.status_code == 200
    assert len(owner_history.json()) == 1
