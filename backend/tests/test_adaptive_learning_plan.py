from tests.conftest import auth_headers, pass_current_assessment


def test_learning_plan_requires_authentication(client):
    response = client.get("/api/v1/education/learning-plan")
    assert response.status_code == 401


def test_learning_plan_exposes_measured_rules_and_locked_prerequisites(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/education/learning-plan", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["generated_from"] == "measured_rules"
    assert "advisory" in payload["advisory_notice"].lower()
    assert [item["sequence"] for item in payload["items"]] == [1, 2, 3, 4]

    first = payload["items"][0]
    assert first["lesson_slug"] == "financial-statements-foundations"
    assert first["state"] == "recommended"
    assert first["recommended_difficulty"] == "foundation"
    assert first["mastery_threshold"] == 70
    assert {signal["kind"] for signal in first["signals"]} >= {
        "lesson_progress",
        "competency_trend",
        "prerequisite_status",
    }
    assert all(signal["measured"] is True for signal in first["signals"])

    locked = next(item for item in payload["items"] if item["lesson_slug"] == "valuation-and-cash-flow")
    assert locked["state"] == "locked"
    prerequisite_signal = next(signal for signal in locked["signals"] if signal["kind"] == "prerequisite_status")
    assert prerequisite_signal["value"] == "locked"
    assert "financial-statements-foundations" in prerequisite_signal["explanation"]


def test_learning_plan_is_deterministic(client):
    headers = auth_headers(client)
    first = client.get("/api/v1/education/learning-plan", headers=headers)
    second = client.get("/api/v1/education/learning-plan", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_repeated_failures_receive_highest_remediation_priority(client):
    headers = auth_headers(client)
    for _ in range(2):
        assessment = client.get("/api/v1/education/assessment", headers=headers).json()
        response = client.post(
            "/api/v1/education/assessment",
            headers=headers,
            json={"question_id": assessment["question"]["id"], "selected_option": 0},
        )
        assert response.status_code == 200
        assert response.json()["passed"] is False

    payload = client.get("/api/v1/education/learning-plan", headers=headers).json()
    first = payload["items"][0]
    assert first["lesson_slug"] == "financial-statements-foundations"
    assert first["state"] == "remediation"
    assert first["priority"] == 0
    assert first["recommended_difficulty"] == "foundation"
    failure_signal = next(signal for signal in first["signals"] if signal["kind"] == "failure_streak")
    assert failure_signal["value"] == "2"


def test_learning_plan_progress_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="plan-owner@example.com")
    client.put(
        "/api/v1/education/lessons/evidence-quality-and-bias/progress",
        headers=owner_headers,
        json={"status": "in_progress", "score": 40},
    )
    owner = client.get("/api/v1/education/learning-plan", headers=owner_headers).json()
    assert owner["items"][0]["lesson_slug"] == "evidence-quality-and-bias"
    assert owner["items"][0]["state"] == "remediation"

    other_headers = auth_headers(client, email="plan-other@example.com")
    other = client.get("/api/v1/education/learning-plan", headers=other_headers).json()
    assert other["items"][0]["lesson_slug"] == "financial-statements-foundations"
    assert other["items"][0]["state"] == "recommended"


def test_completed_curriculum_returns_explicit_completed_state(client):
    headers = auth_headers(client)
    for _ in range(4):
        pass_current_assessment(client, headers)

    response = client.get("/api/v1/education/learning-plan", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["items"] == []
