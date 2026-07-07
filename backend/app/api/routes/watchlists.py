from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    tickers: list[str] = Field(default_factory=list)


@router.post("")
def create_watchlist(payload: WatchlistCreate):
    return {
        "status": "mock",
        "watchlist": {
            "name": payload.name,
            "tickers": [ticker.upper() for ticker in payload.tickers],
        },
        "message": "Watchlist API contract initialized. Persistence will be added with the database layer.",
    }


@router.get("")
def list_watchlists():
    return {
        "status": "mock",
        "watchlists": [],
        "message": "No persisted watchlists yet. Database models are the next backend milestone.",
    }
