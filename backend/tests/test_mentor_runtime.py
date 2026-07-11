from app.services.mentor import MentorOrchestrator
from tests.conftest import auth_headers


def test_intent_classifier_routes_specialists():
    orchestrator = MentorOrchestrator()

    assert orchestrator.classify("Explain discounted cash flow").persona == "Learning Coach"
    assert orchestrator.classify("Analyze company earnings evidence").persona == "Research Mentor"
    assert orchestrator.classify("How should I diversify my portfolio?").persona == "Portfolio Mentor"
    assert orchestrator.classify("How do interest rates affect the economy?").persona == "Economics Mentor"


def test_compose_returns_explainable_contract():
    payload = MentorOrchestrator().compose(
        "Help me review valuation assumptions",
        {"active_lesson": "valuation-101", "active_report": "report-123"},
    )

    assert payload["intent"] in {"finance", "education"}
    assert payload["answer"]
    assert payload["evidence"]
    assert payload["reasoning"]
    assert payload["assumptions"]
    assert payload["confidence"] == "moderate"
    assert any(item["action_type"] == "research_report" for item in payload["recommendations"])


def test_authenticated_chat_persists_and_reopens(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/v1/mentor/chat",
        headers=headers,
        json={
            "message": "Analyze the evidence in my company research",
            "context": {"active_report": "report-123", "goal": "Improve evidence quality"},
        },
    )

    assert created.status_code == 201
    response = created.json()
    assert response["conversation_id"] > 0
    assert response["intent"] == "research"
    assert response["persona"] == "Research Mentor"
    assert response["recommendations"]

    conversation_id = response["conversation_id"]
    continued = client.post(
        "/api/v1/mentor/chat",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "message": "What assumption should I challenge first?",
            "context": {"mastery_gap": "confidence calibration"},
        },
    )
    assert continued.status_code == 201
    assert continued.json()["conversation_id"] == conversation_id

    history = client.get(f"/api/v1/mentor/conversations/{conversation_id}", headers=headers)
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user", "assistant"]


def test_chat_resolves_owned_research_context(client):
    headers = auth_headers(client)
    project = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={
            "title": "Semiconductor moat review",
            "description": "Review industry structure",
            "objective": "Validate durable competitive advantages",
            "context": {"sector": "technology"},
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    session = client.post(
        f"/api/v1/research-projects/{project_id}/sessions",
        headers=headers,
        json={
            "title": "Primary source review",
            "objective": "Challenge the current thesis",
            "context": {"stage": "evidence"},
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    created = client.post(
        "/api/v1/mentor/chat",
        headers=headers,
        json={
            "message": "Challenge the evidence in this project",
            "context": {
                "research_project_id": str(project_id),
                "research_session_id": str(session_id),
            },
        },
    )
    assert created.status_code == 201

    history = client.get(
        f"/api/v1/mentor/conversations/{created.json()['conversation_id']}",
        headers=headers,
    )
    assert history.status_code == 200
    context = history.json()["active_context"]
    assert context["research_project"]["title"] == "Semiconductor moat review"
    assert context["research_project"]["objective"] == "Validate durable competitive advantages"
    assert context["research_session"]["title"] == "Primary source review"
    assert context["research_session"]["project_id"] == project_id


def test_chat_rejects_research_context_owned_by_another_user(client):
    owner_headers = auth_headers(client, email="research-owner@example.com")
    project = client.post(
        "/api/v1/research-projects",
        headers=owner_headers,
        json={"title": "Private research", "context": {}},
    )
    assert project.status_code == 201

    other_headers = auth_headers(client, email="mentor-user@example.com")
    response = client.post(
        "/api/v1/mentor/chat",
        headers=other_headers,
        json={
            "message": "Review this project",
            "context": {"research_project_id": project.json()["id"]},
        },
    )
    assert response.status_code == 404


def test_conversation_is_isolated_by_user(client):
    owner_headers = auth_headers(client, email="owner@example.com")
    created = client.post(
        "/api/v1/mentor/chat",
        headers=owner_headers,
        json={"message": "Teach me risk management"},
    )
    conversation_id = created.json()["conversation_id"]

    other_headers = auth_headers(client, email="other@example.com")
    forbidden = client.get(f"/api/v1/mentor/conversations/{conversation_id}", headers=other_headers)
    assert forbidden.status_code == 404
