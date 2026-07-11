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
