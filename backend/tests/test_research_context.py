from tests.conftest import auth_headers


def test_research_context_endpoint(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research/context/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert payload["quote"]["symbol"] == "AAPL"
    assert payload["quote"]["source"] == "mock-market-data"
    assert payload["news"][0]["source"] == "mock-news"
