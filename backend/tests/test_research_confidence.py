from tests.conftest import auth_headers


def test_research_confidence_endpoint(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research/confidence/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["item_count"] >= 2
    assert float(payload["confidence"]) > 0
