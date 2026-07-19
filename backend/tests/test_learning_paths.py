from tests.conftest import auth_headers, pass_current_assessment


def lesson_by_slug(payload: dict, slug: str) -> dict:
    return next(lesson for lesson in payload["lessons"] if lesson["slug"] == slug)


def test_initial_path_locks_dependent_lessons(client):
    headers = auth_headers(client)
    payload = client.get("/api/v1/education", headers=headers).json()

    financials = lesson_by_slug(payload, "financial-statements-foundations")
    valuation = lesson_by_slug(payload, "valuation-and-cash-flow")
    evidence = lesson_by_slug(payload, "evidence-quality-and-bias")
    thesis = lesson_by_slug(payload, "research-thesis-construction")

    assert financials["path_state"] == "recommended"
    assert evidence["path_state"] == "available"
    assert valuation["path_state"] == "locked"
    assert valuation["prerequisites"] == ["financial-statements-foundations"]
    assert "Financial Statements Foundations" in valuation["path_reason"]
    assert thesis["path_state"] == "locked"
    assert thesis["prerequisites"] == ["evidence-quality-and-bias"]
    assert "Evidence Quality and Bias" in thesis["path_reason"]


def test_locked_lesson_cannot_be_started(client):
    headers = auth_headers(client)
    response = client.put(
        "/api/v1/education/lessons/valuation-and-cash-flow/progress",
        headers=headers,
        json={"status": "in_progress", "score": None},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Lesson prerequisites are not complete"


def test_completing_prerequisite_unlocks_and_recommends_dependent_lesson(client):
    headers = auth_headers(client)
    result = pass_current_assessment(client, headers)
    payload = result["education_hub"]
    valuation = lesson_by_slug(payload, "valuation-and-cash-flow")

    assert payload["recommended_lesson_slug"] == "valuation-and-cash-flow"
    assert valuation["path_state"] == "recommended"
    assert "prerequisite lessons are complete" in valuation["path_reason"]


def test_remediation_overrides_available_progression(client):
    headers = auth_headers(client)
    pass_current_assessment(client, headers)
    response = client.put(
        "/api/v1/education/lessons/valuation-and-cash-flow/progress",
        headers=headers,
        json={"status": "in_progress", "score": 45},
    )
    assert response.status_code == 200
    payload = response.json()
    valuation = lesson_by_slug(payload, "valuation-and-cash-flow")

    assert payload["recommended_lesson_slug"] == "valuation-and-cash-flow"
    assert valuation["path_state"] == "remediation"
    assert "45%" in valuation["path_reason"]
    assert "70%" in valuation["path_reason"]


def test_completed_path_states_remain_stable(client):
    headers = auth_headers(client)
    result = None
    for _ in range(4):
        result = pass_current_assessment(client, headers)

    assert result is not None
    payload = result["education_hub"]
    assert payload["recommended_lesson_slug"] is None
    assert all(lesson["path_state"] == "completed" for lesson in payload["lessons"])
