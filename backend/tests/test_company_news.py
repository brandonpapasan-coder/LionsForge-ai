from tests.conftest import auth_headers


def test_company_news_endpoint(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/news/company/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["articles"][0]["source"] == "mock-news"
