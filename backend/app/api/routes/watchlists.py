from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.watchlists import SavedListCreate, SavedListRead
from app.services.saved_list_service import create_saved_list, list_saved_lists

router = APIRouter()


@router.post("", response_model=SavedListRead)
def create_watchlist(
    payload: SavedListCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedListRead:
    return create_saved_list(db, owner_id=current_user.id, payload=payload)


@router.get("", response_model=list[SavedListRead])
def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedListRead]:
    return list_saved_lists(db, owner_id=current_user.id)
