from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.watchlists import SavedListCreate, SavedListRead
from app.services.saved_list_service import create_saved_list, list_saved_lists

router = APIRouter()


@router.post("", response_model=SavedListRead)
def create_watchlist(
    payload: SavedListCreate,
    owner_id: int = Query(default=1, ge=1, description="Temporary owner id until auth dependency is added."),
    db: Session = Depends(get_db),
) -> SavedListRead:
    return create_saved_list(db, owner_id=owner_id, payload=payload)


@router.get("", response_model=list[SavedListRead])
def list_watchlists(
    owner_id: int = Query(default=1, ge=1, description="Temporary owner id until auth dependency is added."),
    db: Session = Depends(get_db),
) -> list[SavedListRead]:
    return list_saved_lists(db, owner_id=owner_id)
