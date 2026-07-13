from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.knowledge_memory import KnowledgeMemory
from tests.conftest import auth_headers


def create_project(client, headers, title="Quality Project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Measure institutional knowledge quality"},
    )
    assert response.status_code == 201
    return response.json()


def create_approved_evidence(client, headers, project_id, claim, index=1):
    created = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://quality{index}.example.com/report",
            "source_title": f"Quality report {index}",
            "publisher": "Quality Institute",
            "author": "Research Reviewer",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary",
            "claim": claim,
            "excerpt": claim,
            "stance": "supports",
        },
    )
    assert created.status_code == 201
    evidence = created.json()
    reviewed = client.patch(
        f"/api/v1/evidence-intelligence/{evidence['id']}/review",
        headers=headers,
        json={"validation_status": "approved", "reviewer_notes": "Verified"},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def complete_and_promote(client, headers, project_id, claim, title="Quality mission"):
    create_approved_evidence(client, headers, project_id, claim)
    mission_response = client.post(
        "/api/v1/missions",
        headers=headers,
        json={
            "project_id": project_id,
            "title": title,
            "objective": "Produce durable quality knowledge",
            "success_criteria": ["Snapshot persisted"],
        },
    )
    assert mission_response.status_code == 201
    mission = mission_response.json()
    for _ in range(7):
        advanced = client.post(
            f"/api/v1/missions/{mission['id']}/advance",
            headers=headers,
        )
        assert advanced.status_code == 200
        mission = advanced.json()
    promoted = client.post(
        f"/api/v1/knowledge-memory/projects/{project_id}/promote-mission/{mission['id']}",
        headers=headers,
    )
    assert promoted.status_code == 200
    return promoted.json()["memories"]


def test_empty_dashboard_is_deterministic(client):
    headers = auth_headers(client, email="quality-empty@example.com")
    response = client.get("/api/v1/knowledge-quality/dashboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["methodology_version"] == "knowledge-quality-v1"
    assert payload["memories"]["total"] == 0
    assert payload["evidence_total"] == 0
    assert payload["health_score"] == 0.25
    assert payload["top_risks"] == []
    assert payload["recent_activity"] == []


def test_populated_project_dashboard_and_activity(client):
    headers = auth_headers(client, email="quality-populated@example.com")
    project = create_project(client, headers)
    memories = complete_and_promote(
        client,
        headers,
        project["id"],
        "Validated knowledge improves institutional decision quality",
    )
    generated = client.post(
        f"/api/v1/research-planning/projects/{project['id']}/generate",
        headers=headers,
    )
    assert generated.status_code == 200

    response = client.get(
        f"/api/v1/knowledge-quality/projects/{project['id']}",
        headers=headers,
    )
    activity = client.get(
        f"/api/v1/knowledge-quality/projects/{project['id']}/activity",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project["id"]
    assert payload["memories"]["total"] == len(memories)
    assert payload["evidence_approved"] == 1
    assert payload["evidence_coverage_ratio"] > 0
    assert payload["average_confidence"] > 0
    assert payload["missions"]["completed"] == 1
    assert payload["planning"]["total"] >= 1
    assert payload["top_priorities"]
    assert activity.status_code == 200
    assert any(item["record_type"] == "knowledge_memory" for item in activity.json())


def test_stale_and_contested_knowledge_surface_as_risks(client):
    headers = auth_headers(client, email="quality-risk@example.com")
    project = create_project(client, headers, "Risk Project")
    memories = complete_and_promote(
        client,
        headers,
        project["id"],
        "Risk reviews should preserve contested institutional knowledge",
    )
    memory = memories[0]
    contested = client.patch(
        f"/api/v1/knowledge-memory/{memory['id']}",
        headers=headers,
        json={"status": "contested", "confidence": 0.4},
    )
    assert contested.status_code == 200

    with SessionLocal() as db:
        stored = db.scalar(select(KnowledgeMemory).where(KnowledgeMemory.id == memory["id"]))
        assert stored is not None
        stored.updated_at = datetime.utcnow() - timedelta(days=181)
        db.commit()

    risks = client.get(
        f"/api/v1/knowledge-quality/projects/{project['id']}/risks",
        headers=headers,
    )
    dashboard = client.get(
        f"/api/v1/knowledge-quality/projects/{project['id']}",
        headers=headers,
    )

    assert risks.status_code == 200
    risk_types = {item["risk_type"] for item in risks.json()}
    assert "contested_knowledge" in risk_types
    assert "stale_knowledge" in risk_types
    assert dashboard.status_code == 200
    assert dashboard.json()["memories"]["contested"] >= 1
    assert dashboard.json()["memories"]["stale"] >= 1
    assert dashboard.json()["review_backlog"] >= 1


def test_project_scoping_and_owner_isolation(client):
    owner_headers = auth_headers(client, email="quality-owner@example.com")
    first = create_project(client, owner_headers, "Quality Alpha")
    second = create_project(client, owner_headers, "Quality Beta")
    first_memories = complete_and_promote(
        client,
        owner_headers,
        first["id"],
        "Project-scoped quality metrics must remain isolated",
        title="Alpha quality mission",
    )
    second_memories = complete_and_promote(
        client,
        owner_headers,
        second["id"],
        "Organization dashboards aggregate across owned projects",
        title="Beta quality mission",
    )

    first_dashboard = client.get(
        f"/api/v1/knowledge-quality/projects/{first['id']}",
        headers=owner_headers,
    )
    organization = client.get(
        "/api/v1/knowledge-quality/dashboard",
        headers=owner_headers,
    )

    assert first_dashboard.status_code == 200
    assert first_dashboard.json()["memories"]["total"] == len(first_memories)
    assert organization.status_code == 200
    assert organization.json()["memories"]["total"] == len(first_memories) + len(second_memories)

    other_headers = auth_headers(client, email="quality-other@example.com")
    assert client.get(
        f"/api/v1/knowledge-quality/projects/{first['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/knowledge-quality/projects/{first['id']}/risks",
        headers=other_headers,
    ).status_code == 404
