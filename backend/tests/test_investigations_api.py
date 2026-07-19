from tests.conftest import auth_headers


INVESTIGATIONS_URL = "/api/v1/investigations"


def create_investigation(client, headers, *, title="Evidence quality review", question="Does the evidence support the claim?"):
    response = client.post(
        INVESTIGATIONS_URL,
        headers=headers,
        json={"title": title, "research_question": question},
    )
    assert response.status_code == 201
    return response.json()


def test_investigations_require_authentication(client):
    assert client.get(INVESTIGATIONS_URL).status_code == 401
    assert client.post(INVESTIGATIONS_URL, json={"title": "Test", "research_question": "Question?"}).status_code == 401


def test_create_list_read_and_update_owned_investigation(client):
    headers = auth_headers(client, email="investigation-owner@example.com")
    created = create_investigation(client, headers)
    assert created["status"] == "open"
    assert created["title"] == "Evidence quality review"

    listing = client.get(INVESTIGATIONS_URL, headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [created["id"]]

    read = client.get(f"{INVESTIGATIONS_URL}/{created['id']}", headers=headers)
    assert read.status_code == 200
    assert read.json()["research_question"] == "Does the evidence support the claim?"

    updated = client.patch(
        f"{INVESTIGATIONS_URL}/{created['id']}",
        headers=headers,
        json={"status": "in_review", "title": "Updated evidence review"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_review"
    assert updated.json()["title"] == "Updated evidence review"
    assert updated.json()["updated_at"] >= created["updated_at"]


def test_investigations_are_strictly_owner_isolated(client):
    owner_headers = auth_headers(client, email="investigation-private-owner@example.com")
    created = create_investigation(client, owner_headers, title="Private investigation")

    other_headers = auth_headers(client, email="investigation-private-other@example.com")
    assert client.get(INVESTIGATIONS_URL, headers=other_headers).json() == []
    assert client.get(f"{INVESTIGATIONS_URL}/{created['id']}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"{INVESTIGATIONS_URL}/{created['id']}",
            headers=other_headers,
            json={"status": "validated"},
        ).status_code
        == 404
    )


def test_list_orders_by_latest_update(client):
    headers = auth_headers(client, email="investigation-order@example.com")
    first = create_investigation(client, headers, title="First investigation")
    second = create_investigation(client, headers, title="Second investigation")

    response = client.patch(
        f"{INVESTIGATIONS_URL}/{first['id']}",
        headers=headers,
        json={"status": "in_review"},
    )
    assert response.status_code == 200

    listing = client.get(INVESTIGATIONS_URL, headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [first["id"], second["id"]]


def test_invalid_values_and_blank_updates_are_rejected(client):
    headers = auth_headers(client, email="investigation-validation@example.com")

    blank_question = client.post(
        INVESTIGATIONS_URL,
        headers=headers,
        json={"title": "Invalid", "research_question": "   "},
    )
    assert blank_question.status_code == 422

    created = create_investigation(client, headers)
    invalid_status = client.patch(
        f"{INVESTIGATIONS_URL}/{created['id']}",
        headers=headers,
        json={"status": "executing_trade"},
    )
    assert invalid_status.status_code == 422

    empty_update = client.patch(f"{INVESTIGATIONS_URL}/{created['id']}", headers=headers, json={})
    assert empty_update.status_code == 422
