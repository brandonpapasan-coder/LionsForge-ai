from tests.conftest import auth_headers
from tests.test_saved_record_evidence_trace import create_evidence, create_memory, create_project


def get_inventory(client, headers, suffix=""):
    response = client.get(
        f"/api/v1/knowledge-memory/evidence-health/inventory{suffix}",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_evidence_health_inventory_orders_weakest_first_and_aggregates(client):
    headers = auth_headers(client, email="memory-health-inventory@example.com")
    project = create_project(client, headers, "Evidence health inventory")
    support = create_evidence(client, headers, project["id"])
    contradiction = create_evidence(
        client,
        headers,
        project["id"],
        source_url="https://example.org/inventory-contradiction",
        stance="contradicts",
    )

    contested = create_memory(client, headers, project["id"], [support["id"], contradiction["id"]])
    unavailable = create_memory(client, headers, project["id"], [999991])
    unsupported = create_memory(client, headers, project["id"], [])
    weak = create_memory(client, headers, project["id"], [support["id"]])

    body = get_inventory(client, headers)

    ids = [item["memory_id"] for item in body["items"]]
    assert ids.index(contested["id"]) < ids.index(unavailable["id"])
    assert ids.index(unavailable["id"]) < ids.index(unsupported["id"])
    assert ids.index(unsupported["id"]) < ids.index(weak["id"])
    assert body["total_count"] == 4
    assert body["by_classification"]["contested"] == 1
    assert body["by_classification"]["unavailable"] == 1
    assert body["by_classification"]["unsupported"] == 1
    assert body["by_classification"]["weak"] == 1


def test_evidence_health_inventory_filters_by_project_and_classification(client):
    headers = auth_headers(client, email="memory-health-filter@example.com")
    first_project = create_project(client, headers, "First inventory project")
    second_project = create_project(client, headers, "Second inventory project")
    first = create_memory(client, headers, first_project["id"], [])
    create_memory(client, headers, second_project["id"], [999992])

    body = get_inventory(
        client,
        headers,
        f"?project_id={first_project['id']}&classification=unsupported",
    )

    assert body["project_id"] == first_project["id"]
    assert body["classification"] == "unsupported"
    assert body["total_count"] == 1
    assert [item["memory_id"] for item in body["items"]] == [first["id"]]
    assert body["by_classification"] == {"unsupported": 1}


def test_evidence_health_inventory_enforces_owner_isolation(client):
    owner_headers = auth_headers(client, email="memory-health-owner@example.com")
    other_headers = auth_headers(client, email="memory-health-other@example.com")
    owner_project = create_project(client, owner_headers, "Owner inventory project")
    other_project = create_project(client, other_headers, "Other inventory project")
    owner_memory = create_memory(client, owner_headers, owner_project["id"], [])
    create_memory(client, other_headers, other_project["id"], [])

    body = get_inventory(client, owner_headers)

    assert body["total_count"] == 1
    assert [item["memory_id"] for item in body["items"]] == [owner_memory["id"]]
