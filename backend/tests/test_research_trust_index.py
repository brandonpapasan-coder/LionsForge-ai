from tests.conftest import auth_headers


def create_project(client, headers, title="RTI project"):
    response = client.post(
        "/api/v1/research-projects",
        headers=headers,
        json={"title": title, "objective": "Measure research trust"},
    )
    assert response.status_code == 201
    return response.json()


def create_evidence(client, headers, project_id, index, stance="supports", key=None):
    response = client.post(
        "/api/v1/evidence-intelligence",
        headers=headers,
        json={
            "project_id": project_id,
            "source_url": f"https://source{index}.example.com/report",
            "source_title": f"Research report {index}",
            "publisher": f"Institute {index}",
            "author": f"Researcher {index}",
            "published_at": "2026-07-01T00:00:00",
            "source_type": "primary" if index % 2 else "official",
            "claim": f"Finding {index} supports the mission conclusion.",
            "excerpt": f"Independent measurement {index} produced a documented result.",
            "stance": stance,
            "contradiction_key": key,
            "provenance": {"test_source": index},
        },
    )
    assert response.status_code == 201
    return response.json()


def review_evidence(client, headers, evidence_id, status, notes):
    response = client.patch(
        f"/api/v1/evidence-intelligence/{evidence_id}/review",
        headers=headers,
        json={"validation_status": status, "reviewer_notes": notes},
    )
    assert response.status_code == 200
    return response.json()


def component(body, key):
    return next(item for item in body["components"] if item["key"] == key)


def test_project_rti_explains_components_and_recommendations(client):
    headers = auth_headers(client, email="rti@example.com")
    project = create_project(client, headers)

    first = create_evidence(client, headers, project["id"], 1, key="mission-outcome")
    for index in range(2, 6):
        create_evidence(client, headers, project["id"], index, key="mission-outcome")

    review_evidence(client, headers, first["id"], "approved", "Reviewed against source")

    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["evidence_count"] == 5
    assert body["supporting_count"] == 5
    assert body["approved_count"] == 1
    assert body["review_event_count"] == 1
    assert body["reviewed_evidence_count"] == 1
    assert body["review_reversal_count"] == 0
    assert body["methodology_version"] == "rti-v2"
    assert 0 <= body["overall_score"] <= 100
    assert len(body["components"]) == 7
    assert {item["key"] for item in body["components"]} == {
        "evidence_quality",
        "source_diversity",
        "corroboration",
        "freshness",
        "human_validation",
        "validation_stability",
        "completeness",
    }
    assert component(body, "validation_stability")["score"] == 100
    assert body["recommended_actions"]


def test_review_reversals_reduce_validation_stability(client):
    headers = auth_headers(client, email="rti-reversal@example.com")
    project = create_project(client, headers, "Reversal project")
    evidence = create_evidence(client, headers, project["id"], 30)

    review_evidence(client, headers, evidence["id"], "approved", "Initial approval")
    stable = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    ).json()

    review_evidence(client, headers, evidence["id"], "needs_review", "Methodology concern")
    review_evidence(client, headers, evidence["id"], "approved", "Concern resolved")
    reversed_body = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    ).json()

    assert stable["review_event_count"] == 1
    assert stable["review_reversal_count"] == 0
    assert reversed_body["review_event_count"] == 3
    assert reversed_body["reviewed_evidence_count"] == 1
    assert reversed_body["review_reversal_count"] == 2
    assert component(reversed_body, "validation_stability")["score"] < component(stable, "validation_stability")["score"]
    assert any("reversal" in limitation.lower() for limitation in reversed_body["limitations"])


def test_project_governance_snapshot_embeds_rti_and_ordered_review_history(client):
    headers = auth_headers(client, email="governance-snapshot@example.com")
    project = create_project(client, headers, "Governed research")
    evidence = create_evidence(client, headers, project["id"], 40)
    review_evidence(client, headers, evidence["id"], "approved", "Initial validation")
    review_evidence(client, headers, evidence["id"], "needs_review", "New concern")

    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}/governance-snapshot",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["project_title"] == "Governed research"
    assert body["project_status"] == project["status"]
    assert body["generated_at"]
    assert body["trust_index"]["methodology_version"] == "rti-v2"
    assert body["trust_index"]["review_event_count"] == 2
    assert [event["validation_status"] for event in body["review_history"]] == ["approved", "needs_review"]
    assert [event["reviewer_notes"] for event in body["review_history"]] == ["Initial validation", "New concern"]


def test_conflicts_reduce_corroboration_and_are_disclosed(client):
    headers = auth_headers(client, email="rti-conflict@example.com")
    project = create_project(client, headers, "Conflict project")
    create_evidence(client, headers, project["id"], 10, "supports", "shared-claim")
    create_evidence(client, headers, project["id"], 11, "contradicts", "shared-claim")

    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conflict_count"] == 1
    assert body["contradicting_count"] == 1
    assert any("conflict" in limitation.lower() for limitation in body["limitations"])


def test_project_rti_is_owner_isolated(client):
    owner_headers = auth_headers(client, email="rti-owner@example.com")
    project = create_project(client, owner_headers, "Private RTI")
    evidence = create_evidence(client, owner_headers, project["id"], 20)
    review_evidence(client, owner_headers, evidence["id"], "approved", "Owner review")

    other_headers = auth_headers(client, email="rti-other@example.com")
    response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}",
        headers=other_headers,
    )
    assert response.status_code == 404

    snapshot_response = client.get(
        f"/api/v1/research-trust-index/projects/{project['id']}/governance-snapshot",
        headers=other_headers,
    )
    assert snapshot_response.status_code == 404
