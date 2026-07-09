from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    statement = select(Company).where(Company.ticker == normalize_ticker(ticker))
    return db.scalar(statement)


def list_companies(db: Session, query: str | None = None, limit: int = 50) -> list[Company]:
    statement = select(Company).order_by(Company.ticker).limit(limit)
    if query:
        normalized_query = f"%{query.strip()}%"
        statement = (
            select(Company)
            .where((Company.ticker.ilike(normalized_query)) | (Company.name.ilike(normalized_query)))
            .order_by(Company.ticker)
            .limit(limit)
        )
    return list(db.scalars(statement).all())


def create_company(db: Session, payload: CompanyCreate) -> Company:
    company = Company(**payload.model_dump())
    company.ticker = normalize_ticker(company.ticker)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company: Company, payload: CompanyUpdate) -> Company:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company: Company) -> None:
    db.delete(company)
    db.commit()
