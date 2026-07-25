from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.remediation_progress import RemediationProgress
from tests.conftest import auth_headers

BASE = "/api/v1/investigations"


def _investigation(client, headers, title="Queue investigation"):
    response = client.post(
        BASE,
        headers=headers,
        json={"title": title, "research_question": "What needs human review?"},
    )
    assert response.status_code == 201
    return response.json()


def _claim(client, headers, investigation_id, statement="A claim requiring review"):
    response = client.post(
        f"{BASE}/{investigation_id}/claims",
        headers=headers,
        json={"statement": statement},
    )
    assert response.status_code == 201
    return response.json()


def test_review_queue_requires_authentication(client):
    response = client.get(f"{BASE}/review-queue")
    assert response.status_code == 401


def test_review_queue_returns_explicit_empty_state(client):
    headers = auth_headers(client, email="queue-empty@example.com")
    response = client.get(f"{BASE}/review-queue", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["item_count"] == 0
    assert payload["items"] == []
    assert "does not establish truth" in payload["interpretation_notice"]


def test_review_queue_detects_stored_reasons_and_orders_by_priority(client):
    headers = auth_headers(client, email="queue-events@example.com")
    investigation = _investigation(client, headers)
    claim = _claim(client, headers, investigation["id"])

    evidence = client.post(
        f"{BASE}/claims/{claim['id']}/evidence",
        headers=headers,
        json={
            "source_title": "Contradicting source",
            "source_url": "https://example.com/contradiction",
            "evidence_type": "primary",
            "relationship": "contradicts",
            "notes": "Direct contradiction.",
        },
    )
    assert evidence.status_code == 201

    judgment = client.post(
        f"{BASE}/claims/{claim['id']}/judgments",
        headers=headers,
        json={
            "validation_status": "mixed",
            "confidence_level": "medium",
            "rationale": "Initial review.",
            "unresolved_questions": "Reconcile the source.",
        },
    )
    assert judgment.status_code == 201

    updated = client.patch(
        f"{BASE}/claims/{claim['id']}",
        headers=headers,
        json={"statement": "An updated claim requiring review"},
    )
    assert updated.status_code == 200

    with SessionLocal() as db:
        user_id = judgment.json()["reviewer_id"]
        now = datetime.utcnow() + timedelta(seconds=1)
        db.add(
            RemediationProgress(
                investigation_id=investigation["id"],
                claim_id=claim["id"],
                owner_id=user_id,
                status="ready_for_review",
                notes="Prepared for review.",
                action_type_snapshot="resolve_contradiction",
                priority_snapshot=5,
                plan_generated_at_snapshot=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    response = client.get(f"{BASE}/review-queue", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    reasons = [item["reason_type"] for item in payload["items"]]
    assert payload["status"] == "active"
    assert reasons == [
        "stale_validation",
        "unresolved_contradiction",
        "remediation_ready_for_review",
    ]
    assert payload["items"][0]["workflow_priority"] == 5
    assert payload["items"][-1]["workflow_priority"] == 3
    assert len({item["item_key"] for item in payload["items"]}) == 3
    assert all(item["source_tables"] for item in payload["items"])


def test_review_queue_detects_missing_validation_and_blocked_remediation(client):
    headers = auth_headers(client, email="queue-blocked@example.com")
    investigation = _investigation(client, headers, title="Blocked work")
    claim = _claim(client, headers, investigation["id"], statement="Blocked claim")

    with SessionLocal() as db:
        from app.models.user import User

        user = db.query(User).filter(User.email == "queue-blocked@example.com").one()
        now = datetime.utcnow()
        db.add(
            RemediationProgress(
                investigation_id=investigation["id"],
                claim_id=claim["id"],
                owner_id=user.id,
                status="blocked",
                notes="Awaiting a source.",
                action_type_snapshot="attach_initial_evidence",
                priority_snapshot=5,
                plan_generated_at_snapshot=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    payload = client.get(f"{BASE}/review-queue", headers=headers).json()
    assert [item["reason_type"] for item in payload["items"]] == [
        "blocked_remediation",
        "missing_validation",
    ]


def test_review_queue_isolates_owners(client):
    first_headers = auth_headers(client, email="queue-owner-one@example.com")
    first_investigation = _investigation(client, first_headers, title="Owner one")
    _claim(client, first_headers, first_investigation["id"], statement="Owner one claim")

    second_headers = auth_headers(client, email="queue-owner-two@example.com")
    second_investigation = _investigation(client, second_headers, title="Owner two")
    _claim(client, second_headers, second_investigation["id"], statement="Owner two claim")

    payload = client.get(f"{BASE}/review-queue", headers=first_headers).json()
    assert payload["item_count"] == 1
    assert payload["items"][0]["investigation_title"] == "Owner one"
    assert payload["items"][0]["claim_statement"] == "Owner one claim"
