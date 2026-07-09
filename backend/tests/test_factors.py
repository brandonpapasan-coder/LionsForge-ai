def test_factor_score_returns_explainable_breakdown(client):
    response = client.get("/api/v1/factors/NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["composite_score"] >= "0.000000"
    assert payload["rating"] in {"avoid", "watch", "neutral", "outperform"}
    assert len(payload["factors"]) == 7
    assert all("explanation" in factor for factor in payload["factors"])
    assert "LionsForge factor score" in payload["explanation"]


def test_factor_rankings_are_sorted_and_ranked(client):
    response = client.get("/api/v1/factors/rankings/list?symbols=TSLA&symbols=MSFT&symbols=NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3
    scores = [item["composite_score"] for item in payload["results"]]
    assert scores == sorted(scores, reverse=True)
    assert [item["rank"] for item in payload["results"]] == [1, 2, 3]


def test_screener_filters_by_min_score(client):
    response = client.post(
        "/api/v1/factors/screener",
        json={"symbols": ["TSLA", "MSFT", "NVDA", "JNJ"], "min_score": "70"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert all(item["composite_score"] >= "70.000000" for item in payload["results"])


def test_screener_filters_by_rating(client):
    response = client.post(
        "/api/v1/factors/screener",
        json={"symbols": ["TSLA", "MSFT", "NVDA", "JNJ"], "rating": "neutral"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert all(item["rating"] == "neutral" for item in payload["results"])


def test_factor_compare_returns_leaders_and_laggards(client):
    response = client.get("/api/v1/factors/compare/list?symbols=TSLA&symbols=MSFT&symbols=NVDA&symbols=JNJ")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"]
    assert payload["leaders"]
    assert payload["laggards"]
    assert payload["leaders"][0]["composite_score"] >= payload["laggards"][0]["composite_score"]


def test_unknown_symbol_uses_deterministic_default_factor_data(client):
    response = client.get("/api/v1/factors/XYZ")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "XYZ"
    assert len(payload["factors"]) == 7
    assert all(factor["confidence"] == "medium" for factor in payload["factors"])
