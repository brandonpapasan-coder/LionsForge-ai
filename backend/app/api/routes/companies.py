from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company_service import (
    create_company,
    delete_company,
    get_company_by_ticker,
    list_companies,
    update_company,
)

router = APIRouter()


@router.get("", response_model=list[CompanyRead])
def list_company_profiles(
    query: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyRead]:
    _ = current_user
    return list_companies(db, query=query, limit=limit)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company_profile(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyRead:
    _ = current_user
    existing = get_company_by_ticker(db, payload.ticker)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company already exists")
    return create_company(db, payload)


@router.get("/{ticker}", response_model=CompanyRead)
def get_company_profile(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyRead:
    _ = current_user
    company = get_company_by_ticker(db, ticker)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/{ticker}", response_model=CompanyRead)
def update_company_profile(
    ticker: str,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyRead:
    _ = current_user
    company = get_company_by_ticker(db, ticker)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return update_company(db, company, payload)


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_profile(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    _ = current_user
    company = get_company_by_ticker(db, ticker)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    delete_company(db, company)
