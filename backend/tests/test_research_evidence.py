from tests.conftest import auth_headers


def test_research_evidence_endpoint(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research/evidence/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    categories = {item["category"] for item in payload["items"]}
    assert "market_quote" in categories
    assert "company_news" in categories
