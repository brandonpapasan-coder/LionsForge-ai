from app.services.assessments import ASSESSMENT_BANK
from tests.conftest import auth_headers


HUB_URL = "/api/v1/education"
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
    return response.json()


def test_repeated_failures_trigger_targeted_foundation_remediation(client):
    headers = auth_headers(client, email="repeated-remediation@example.com")

    first = submit_current_assessment(client, headers, correct=False)
    second = submit_current_assessment(client, headers, correct=False)
    assert first["passed"] is False
    assert second["passed"] is False

    hub = client.get(HUB_URL, headers=headers)
    assert hub.status_code == 200
    hub_payload = hub.json()
    assert hub_payload["recommended_lesson_slug"] == first["lesson_slug"]
    assert "2 consecutive unsuccessful attempts" in hub_payload["recommendation_reason"]
    recommended = next(
        lesson for lesson in hub_payload["lessons"] if lesson["slug"] == hub_payload["recommended_lesson_slug"]
    )
    assert recommended["path_state"] == "remediation"
    assert "targeted remediation" in recommended["path_reason"].lower()

    assessment = client.get(ASSESSMENT_URL, headers=headers)
    assert assessment.status_code == 200
    assessment_payload = assessment.json()
    assert assessment_payload["difficulty"] == "foundation"
    assert "2 consecutive unsuccessful attempts" in assessment_payload["difficulty_reason"]
    assert "correct_option" not in assessment_payload["question"]


def test_later_pass_clears_repeated_failure_remediation(client):
    headers = auth_headers(client, email="remediation-recovery@example.com")

    submit_current_assessment(client, headers, correct=False)
    submit_current_assessment(client, headers, correct=False)
    recovered = submit_current_assessment(client, headers, correct=True)
    assert recovered["passed"] is True

    hub = client.get(HUB_URL, headers=headers)
    assert hub.status_code == 200
    payload = hub.json()
    assert "consecutive unsuccessful attempts" not in payload["recommendation_reason"]
    completed = next(lesson for lesson in payload["lessons"] if lesson["slug"] == recovered["lesson_slug"])
    assert completed["path_state"] == "completed"


def test_repeated_failures_are_isolated_by_user(client):
    owner_headers = auth_headers(client, email="remediation-owner@example.com")
    submit_current_assessment(client, owner_headers, correct=False)
    submit_current_assessment(client, owner_headers, correct=False)

    other_headers = auth_headers(client, email="remediation-other@example.com")
    other_assessment = client.get(ASSESSMENT_URL, headers=other_headers)
    assert other_assessment.status_code == 200
    payload = other_assessment.json()
    assert "consecutive unsuccessful attempts" not in payload["difficulty_reason"]


def test_no_history_preserves_mastery_based_selection(client):
    headers = auth_headers(client, email="remediation-no-history@example.com")

    response = client.get(ASSESSMENT_URL, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["difficulty"] == "foundation"
    assert payload["difficulty_reason"].startswith("Foundation difficulty selected because mastery is")
    assert "correct_option" not in payload["question"]
