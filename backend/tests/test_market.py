from tests.conftest import auth_headers


def test_single_quote_requires_auth_and_returns_quote(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/market/quotes/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock-market-data"


def test_batch_quotes(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/market/quotes",
        headers=headers,
        json={"symbols": ["AAPL", "MSFT", "aapl"]},
    )
    assert response.status_code == 200
    symbols = [quote["symbol"] for quote in response.json()]
    assert symbols == ["AAPL", "MSFT"]
