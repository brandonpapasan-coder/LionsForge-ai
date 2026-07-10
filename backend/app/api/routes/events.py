from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.event_intelligence import EventImpactSummary, MarketEvent, MarketEventList
from app.services.event_intelligence_service import build_symbol_event_impact, get_market_event, list_market_events

router = APIRouter()


@router.get("", response_model=MarketEventList)
def list_events_endpoint(
    symbol: str | None = None,
    category: str | None = Query(default=None, pattern="^(earnings|filing|analyst|macro|portfolio_risk|company)$"),
    current_user: User = Depends(get_current_user),
) -> MarketEventList:
    return list_market_events(symbol=symbol, category=category)


@router.get("/{event_id}", response_model=MarketEvent)
def get_event_endpoint(
    event_id: str,
    current_user: User = Depends(get_current_user),
) -> MarketEvent:
    event = get_market_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("/symbol/{symbol}/impact", response_model=EventImpactSummary)
def symbol_event_impact_endpoint(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> EventImpactSummary:
    return build_symbol_event_impact(symbol)
