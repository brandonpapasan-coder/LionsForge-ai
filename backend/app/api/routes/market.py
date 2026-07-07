from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.market import QuoteRead, QuoteRequest
from app.services.market_data_service import get_quote, get_quotes

router = APIRouter()


@router.get("/quotes/{symbol}", response_model=QuoteRead)
def read_quote(symbol: str, current_user: User = Depends(get_current_user)) -> QuoteRead:
    return get_quote(symbol)


@router.post("/quotes", response_model=list[QuoteRead])
def read_quotes(payload: QuoteRequest, current_user: User = Depends(get_current_user)) -> list[QuoteRead]:
    return get_quotes(payload.symbols)


@router.get("/quotes", response_model=list[QuoteRead])
def read_quotes_query(
    symbols: list[str] = Query(..., description="One or more ticker symbols."),
    current_user: User = Depends(get_current_user),
) -> list[QuoteRead]:
    return get_quotes(symbols)
