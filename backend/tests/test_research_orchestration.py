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


def test_orchestrator_returns_auditable_deterministic_outputs():
    request = ResearchOrchestrationRequest(
        question="Should the valuation thesis be revised?",
        symbol="lfai",
        context={"thesis": "Growth exceeds expectations", "source": "internal report"},
    )
    orchestrator = ResearchOrchestrator()

    first = orchestrator.run(request, user_id=7)
    second = orchestrator.run(request, user_id=7)

    assert first.symbol == "LFAI"
    assert first.run_id == second.run_id
    assert [output.role for output in first.agent_outputs] == [
        "research",
        "evidence",
        "risk",
        "synthesis",
    ]
    assert first.synthesis.conclusion
    assert first.evidence_gaps
    assert first.assumptions
    assert first.confidence == "moderate"


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


def test_orchestration_hides_projects_not_owned_by_current_user(client):
    response = client.post(
        "/api/v1/research-orchestration/run",
        headers=auth_headers(client),
        json={
            "question": "Analyze this inaccessible project",
            "project_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Research project not found"
