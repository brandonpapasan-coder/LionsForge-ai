from app.schemas.research_orchestration import ResearchOrchestrationRequest
from app.services.research_orchestration import ResearchOrchestrator
from tests.conftest import auth_headers


def test_planner_deduplicates_roles_and_appends_synthesis():
    request = ResearchOrchestrationRequest(
        question="Evaluate the research thesis",
        requested_roles=["research", "research", "risk"],
    )

    plan = ResearchOrchestrator().plan(request)

    assert [step.role for step in plan] == ["research", "risk", "synthesis"]
    assert [step.order for step in plan] == [1, 2, 3]


def test_orchestrator_returns_auditable_outputs():
    request = ResearchOrchestrationRequest(
        question="Should the valuation thesis be revised?",
        symbol="lfai",
        context={"thesis": "Growth exceeds expectations", "source": "internal report"},
    )

    result = ResearchOrchestrator().run(request, user_id=7)

    assert result.symbol == "LFAI"
    assert result.run_id
    assert [output.role for output in result.agent_outputs] == [
        "research",
        "evidence",
        "risk",
        "synthesis",
    ]
    assert result.synthesis.conclusion
    assert result.evidence_gaps
    assert result.assumptions
    assert result.confidence == "moderate"


def test_orchestration_requires_authentication(client):
    response = client.post(
        "/api/v1/research-orchestration/run",
        json={"question": "Evaluate this research thesis"},
    )

    assert response.status_code == 401


def test_authenticated_orchestration_returns_structured_response(client):
    response = client.post(
        "/api/v1/research-orchestration/run",
        headers=auth_headers(client),
        json={
            "question": "Analyze the evidence and downside risk",
            "symbol": "msft",
            "context": {"active_report": "report-123"},
            "requested_roles": ["evidence", "risk"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "MSFT"
    assert [step["role"] for step in payload["plan"]] == ["evidence", "risk", "synthesis"]
    assert len(payload["agent_outputs"]) == 3
    assert payload["synthesis"]["recommended_actions"]
    assert payload["confidence"] in {"low", "moderate", "high"}
