from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist
from app.schemas.watchlists import SavedListCreate


def normalize_symbols(symbols: list[str]) -> list[str]:
    normalized: set[str] = set()
    for raw_symbol in symbols:
        symbol = raw_symbol.strip().upper()
        if symbol:
            normalized.add(symbol)
    return sorted(normalized)


def create_saved_list(db: Session, owner_id: int, payload: SavedListCreate) -> Watchlist:
    record = Watchlist(
        owner_id=owner_id,
        name=payload.name.strip(),
        tickers=normalize_symbols(payload.symbols),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_saved_lists(db: Session, owner_id: int) -> list[Watchlist]:
    statement = select(Watchlist).where(Watchlist.owner_id == owner_id).order_by(Watchlist.created_at.desc())
    return list(db.scalars(statement))
