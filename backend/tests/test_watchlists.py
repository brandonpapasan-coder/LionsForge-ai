from tests.conftest import auth_headers


def test_create_and_list_watchlists(client):
    headers = auth_headers(client)
    create_response = client.post(
        "/api/v1/watchlists",
        headers=headers,
        json={"name": "Core Tech", "symbols": ["aapl", "MSFT", "AAPL"]},
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["name"] == "Core Tech"
    assert payload["symbols"] == ["AAPL", "MSFT"]

    list_response = client.get("/api/v1/watchlists", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
