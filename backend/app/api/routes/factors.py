from fastapi import APIRouter, Query

from app.schemas.factor import FactorCompareResponse, FactorRankingResponse, FactorScore, ScreenerRequest
from app.services.factor_service import compare_factors, get_factor_score, rank_factors, screen_factors

router = APIRouter()


@router.get("/{symbol}", response_model=FactorScore)
def factor_score_endpoint(symbol: str) -> FactorScore:
    return get_factor_score(symbol)


@router.get("/rankings/list", response_model=FactorRankingResponse)
def factor_rankings_endpoint(symbols: list[str] = Query(default=["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "JNJ"])) -> FactorRankingResponse:
    return rank_factors(symbols)


@router.get("/compare/list", response_model=FactorCompareResponse)
def factor_compare_endpoint(symbols: list[str] = Query(..., min_length=2)) -> FactorCompareResponse:
    return compare_factors(symbols)


@router.post("/screener", response_model=FactorRankingResponse)
def screener_endpoint(payload: ScreenerRequest) -> FactorRankingResponse:
    return screen_factors(payload)
