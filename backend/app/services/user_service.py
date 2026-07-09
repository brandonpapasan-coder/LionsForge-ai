from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_secret_hash, verify_secret
from app.models.user import User
from app.schemas.auth import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=get_secret_hash(payload.secret),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, secret: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_secret(secret, user.hashed_password):
        return None
    return user
