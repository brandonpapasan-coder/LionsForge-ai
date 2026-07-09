from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.watchlist import Watchlist
from app.schemas.portfolio import WatchlistSyncResult
from app.services.saved_list_service import normalize_symbols


def sync_portfolio_to_watchlist(db: Session, owner_id: int, portfolio: Portfolio, watchlist_id: int | None = None) -> WatchlistSyncResult:
    symbols = normalize_symbols([holding.symbol for holding in portfolio.holdings])
    if watchlist_id is None:
        watchlist = Watchlist(owner_id=owner_id, name=f"{portfolio.name} Holdings", tickers=[])
        db.add(watchlist)
        db.flush()
    else:
        statement = select(Watchlist).where(Watchlist.owner_id == owner_id, Watchlist.id == watchlist_id)
        watchlist = db.scalar(statement)
        if watchlist is None:
            watchlist = Watchlist(owner_id=owner_id, name=f"{portfolio.name} Holdings", tickers=[])
            db.add(watchlist)
            db.flush()

    existing = set(normalize_symbols(watchlist.tickers or []))
    added = sorted(set(symbols) - existing)
    watchlist.tickers = sorted(existing | set(symbols))
    db.commit()
    db.refresh(watchlist)

    return WatchlistSyncResult(
        portfolio_id=portfolio.id,
        watchlist_id=watchlist.id,
        added_symbols=added,
        tickers=watchlist.tickers,
    )
