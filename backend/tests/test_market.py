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


def test_historical_prices(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/market/historical/aapl?limit=5", headers=headers)
    assert response.status_code == 200
    prices = response.json()
    assert len(prices) == 5
    assert prices[0]["symbol"] == "AAPL"
    assert prices[0]["source"] == "mock-market-data"
    assert {"date", "open", "high", "low", "close", "volume"}.issubset(prices[0].keys())


def test_historical_prices_require_authentication(client):
    response = client.get("/api/v1/market/historical/AAPL?limit=5")
    assert response.status_code == 401


def test_historical_prices_validate_limit(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/market/historical/AAPL?limit=0", headers=headers)
    assert response.status_code == 422
