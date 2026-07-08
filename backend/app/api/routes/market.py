from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.market import HistoricalPriceRead, QuoteRead, QuoteRequest
from app.services.market_data_service import get_historical_prices, get_quote, get_quotes

router = APIRouter()


@router.get("/quotes/{symbol}", response_model=QuoteRead)
def read_quote(symbol: str, current_user: User = Depends(get_current_user)) -> QuoteRead:
    _ = current_user
    return get_quote(symbol)


@router.post("/quotes", response_model=list[QuoteRead])
def read_quotes(payload: QuoteRequest, current_user: User = Depends(get_current_user)) -> list[QuoteRead]:
    _ = current_user
    return get_quotes(payload.symbols)


@router.get("/quotes", response_model=list[QuoteRead])
def read_quotes_query(
    symbols: list[str] = Query(..., description="One or more ticker symbols."),
    current_user: User = Depends(get_current_user),
) -> list[QuoteRead]:
    _ = current_user
    return get_quotes(symbols)


@router.get("/historical/{symbol}", response_model=list[HistoricalPriceRead])
def read_historical_prices(
    symbol: str,
    limit: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
) -> list[HistoricalPriceRead]:
    _ = current_user
    return get_historical_prices(symbol, limit=limit)
