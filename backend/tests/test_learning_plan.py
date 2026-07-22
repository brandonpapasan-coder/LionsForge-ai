from tests.conftest import auth_headers, pass_current_assessment


def test_learning_plan_requires_authentication(client):
    response = client.get("/api/v1/education/learning-plan")
    assert response.status_code == 401


def test_learning_plan_returns_deterministic_foundation_sequence(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/education/learning-plan", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert "advisory" in payload["advisory_notice"].lower()
    assert [item["lesson_slug"] for item in payload["plan_items"]] == [
        "financial-statements-foundations",
        "evidence-quality-and-bias",
    ]
    assert [item["sequence_position"] for item in payload["plan_items"]] == [1, 2]
    assert all(item["recommendation_type"] == "progression" for item in payload["plan_items"])
    assert all(item["recommended_difficulty"] == "foundation" for item in payload["plan_items"])
    assert all(item["mastery_threshold"] == 70 for item in payload["plan_items"])
    assert payload["plan_items"][0]["supporting_signals"][0]["signal_type"] == "competency_mastery"


def test_learning_plan_prioritizes_low_score_remediation(client):
    headers = auth_headers(client)
    pass_current_assessment(client, headers)
    client.put(
        "/api/v1/education/lessons/valuation-and-cash-flow/progress",
        headers=headers,
        json={"status": "in_progress", "score": 55},
    )

    payload = client.get("/api/v1/education/learning-plan", headers=headers).json()
    first = payload["plan_items"][0]
    assert first["lesson_slug"] == "valuation-and-cash-flow"
    assert first["recommendation_type"] == "remediation"
    assert first["priority_score"] == 815
    assert first["recommended_difficulty"] == "intermediate"
    assert "below the 70% mastery threshold" in first["recommendation_reason"]
    assert [signal["signal_type"] for signal in first["supporting_signals"]] == [
        "latest_lesson_score",
        "competency_mastery",
        "prerequisites_complete",
    ]


def test_learning_plan_reduces_difficulty_after_repeated_failures(client):
    headers = auth_headers(client)
    for _ in range(2):
        assessment = client.get("/api/v1/education/assessment", headers=headers).json()
        result = client.post(
            "/api/v1/education/assessment",
            headers=headers,
            json={"question_id": assessment["question"]["id"], "selected_option": 0},
        )
        assert result.status_code == 200
        assert result.json()["passed"] is False

    payload = client.get("/api/v1/education/learning-plan", headers=headers).json()
    first = payload["plan_items"][0]
    assert first["lesson_slug"] == "financial-statements-foundations"
    assert first["recommendation_type"] == "remediation"
    assert first["recommended_difficulty"] == "foundation"
    assert first["priority_score"] == 1300
    assert first["supporting_signals"][0]["signal_type"] == "unresolved_failure_streak"
    assert first["supporting_signals"][0]["measured_value"] == "2"


def test_learning_plan_is_owner_scoped(client):
    owner_headers = auth_headers(client, email="plan-owner@example.com")
    pass_current_assessment(client, owner_headers)

    other_headers = auth_headers(client, email="plan-other@example.com")
    other = client.get("/api/v1/education/learning-plan", headers=other_headers).json()
    assert other["plan_items"][0]["lesson_slug"] == "financial-statements-foundations"
    assert other["plan_items"][0]["supporting_signals"][0]["measured_value"] == "0%"


def test_learning_plan_returns_completed_state(client):
    headers = auth_headers(client)
    for _ in range(4):
        pass_current_assessment(client, headers)

    response = client.get("/api/v1/education/learning-plan", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["plan_items"] == []
