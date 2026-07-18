from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.evidence import ResearchReviewAction
from app.models.user import User
from tests.conftest import auth_headers
from tests.test_saved_record_evidence_remediation import create_project


def add_action(*, owner_id: int, project_id: int, key: str, priority: str, age_days: int, due_days: int | None = None, status: str = "open"):
    now = datetime.utcnow()
    created_at = now - timedelta(days=age_days)
    with SessionLocal() as db:
        action = ResearchReviewAction(
            owner_id=owner_id,
            project_id=project_id,
            evidence_id=0,
            action_key=key,
            impact_level="high_attention" if priority in {"urgent", "high"} else "review_required",
            governing_rule="saved_record_add_direct_support",
            reason="Evidence remediation requires owner review.",
            action_text="Complete the research evidence remediation step.",
            supporting_event_ids=["memory:1"],
            status=status,
            priority=priority,
            due_at=now + timedelta(days=due_days) if due_days is not None else None,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action.id


def owner_id_for(email: str) -> int:
    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == email))
        assert owner is not None
        return owner.id


def test_escalation_inventory_classifies_filters_and_orders_active_actions(client):
    email = "remediation-escalation@example.com"
    headers = auth_headers(client, email=email)
    project = create_project(client, headers, "Escalation project")
    owner_id = owner_id_for(email)

    critical_id = add_action(owner_id=owner_id, project_id=project["id"], key="critical", priority="urgent", age_days=5)
    overdue_id = add_action(owner_id=owner_id, project_id=project["id"], key="overdue", priority="high", age_days=6)
    aging_id = add_action(owner_id=owner_id, project_id=project["id"], key="aging", priority="normal", age_days=8)
    fresh_id = add_action(owner_id=owner_id, project_id=project["id"], key="fresh", priority="low", age_days=1)
    add_action(owner_id=owner_id, project_id=project["id"], key="resolved", priority="urgent", age_days=90, status="resolved")

    response = client.get("/api/v1/knowledge-memory/evidence-remediation/escalations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["by_state"] == {"fresh": 1, "aging": 1, "overdue": 1, "critical": 1}
    assert [item["follow_up_id"] for item in body["items"]] == [critical_id, overdue_id, aging_id, fresh_id]
    assert all(item["escalation_reason"] and item["recommended_owner_action"] for item in body["items"])

    filtered = client.get(
        f"/api/v1/knowledge-memory/evidence-remediation/escalations?project_id={project['id']}&escalation_state=overdue",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["follow_up_id"] == overdue_id


def test_due_date_drives_overdue_and_critical_escalation(client):
    email = "remediation-due-escalation@example.com"
    headers = auth_headers(client, email=email)
    project = create_project(client, headers, "Due escalation project")
    owner_id = owner_id_for(email)

    overdue_id = add_action(owner_id=owner_id, project_id=project["id"], key="due-overdue", priority="normal", age_days=1, due_days=-2)
    critical_id = add_action(owner_id=owner_id, project_id=project["id"], key="due-critical", priority="urgent", age_days=1, due_days=-3)

    body = client.get("/api/v1/knowledge-memory/evidence-remediation/escalations", headers=headers).json()
    by_id = {item["follow_up_id"]: item for item in body["items"]}
    assert by_id[overdue_id]["escalation_state"] == "overdue"
    assert by_id[overdue_id]["days_overdue"] >= 1
    assert by_id[critical_id]["escalation_state"] == "critical"


def test_escalation_inventory_enforces_owner_isolation(client):
    owner_email = "remediation-escalation-owner@example.com"
    owner_headers = auth_headers(client, email=owner_email)
    other_headers = auth_headers(client, email="remediation-escalation-other@example.com")
    project = create_project(client, owner_headers, "Private escalation project")
    add_action(
        owner_id=owner_id_for(owner_email),
        project_id=project["id"],
        key="private-critical",
        priority="urgent",
        age_days=10,
    )

    body = client.get("/api/v1/knowledge-memory/evidence-remediation/escalations", headers=other_headers).json()
    assert body["total"] == 0
    assert body["items"] == []
