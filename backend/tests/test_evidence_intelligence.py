from tests.conftest import auth_headers


def create_project(client, headers):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": "Evidence project", "objective": "Validate evidence"},
    )
    assert response.status_code == 201
    return response.json()


def evidence_payload(project_id, stance="supports"):
    return {
        "project_id": project_id,
        "source_url": "https://example.com/research",
        "source_title": "Research source",
        "publisher": "Example Institute",
        "author": "A. Researcher",
        "published_at": "2026-07-01T00:00:00",
        "source_type": "primary",
        "claim": "The technology reduced energy use by twenty percent.",
        "excerpt": "Measured energy use fell by twenty percent during the trial.",
        "stance": stance,
        "contradiction_key": "energy-reduction",
        "provenance": {"ingestion_method": "manual"},
    }


def test_evidence_ingestion_scores_and_rejects_duplicates(client):
    headers = auth_headers(client, email="evidence@example.com")
    project = create_project(client, headers)
    payload = evidence_payload(project["id"])

    created = client.post("/api/v1/evidence-intelligence", headers=headers, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["credibility_score"] >= 0.9
    assert 0 <= body["freshness_score"] <= 1
    assert 0 <= body["confidence_score"] <= 1
    assert body["validation_status"] == "unverified"

    duplicate = client.post("/api/v1/evidence-intelligence", headers=headers, json=payload)
    assert duplicate.status_code == 409


def test_review_and_conflict_detection(client):
    headers = auth_headers(client, email="evidence-review@example.com")
    project = create_project(client, headers)

    supporting = evidence_payload(project["id"], "supports")
    assert client.post("/api/v1/evidence-intelligence", headers=headers, json=supporting).status_code == 201

    contradicting = evidence_payload(project["id"], "contradicts")
    contradicting["source_url"] = "https://example.org/counter-study"
    contradicting["source_title"] = "Counter study"
    contradicting["claim"] = "The technology did not reduce energy use."
    contradicting["excerpt"] = "No statistically significant reduction was observed."
    second = client.post("/api/v1/evidence-intelligence", headers=headers, json=contradicting)
    assert second.status_code == 201

    review = client.patch(
        f"/api/v1/evidence-intelligence/{second.json()['id']}/review",
        headers=headers,
        json={"validation_status": "needs_review", "reviewer_notes": "Resolve methodology conflict"},
    )
    assert review.status_code == 200
    assert review.json()["validation_status"] == "needs_review"

    conflicts = client.get(
        f"/api/v1/evidence-intelligence/analysis/conflicts?project_id={project['id']}",
        headers=headers,
    )
    assert conflicts.status_code == 200
    assert conflicts.json()[0]["contradiction_key"] == "energy-reduction"
    assert len(conflicts.json()[0]["supporting"]) == 1
    assert len(conflicts.json()[0]["contradicting"]) == 1
