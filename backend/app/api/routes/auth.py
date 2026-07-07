from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import Token, UserCreate, UserRead
from app.services.user_service import authenticate_user, create_user, get_user_by_email

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    return create_user(db, payload)


@router.post("/login", response_model=Token)
def login(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, payload.email, payload.secret)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=create_access_token(subject=str(user.id)))
