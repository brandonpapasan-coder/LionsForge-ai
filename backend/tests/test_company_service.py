import pytest

from app.db.session import SessionLocal
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company_service import (
    create_company,
    delete_company,
    get_company_by_ticker,
    list_companies,
    normalize_ticker,
    update_company,
)


@pytest.fixture
def db_session(reset_database):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_normalize_ticker():
    assert normalize_ticker(" aapl ") == "AAPL"


def test_company_service_crud(db_session):
    payload = CompanyCreate(
        ticker="aapl",
        name="Apple Inc.",
        exchange="NASDAQ",
        sector="Technology",
        industry="Consumer Electronics",
        country="United States",
        website="https://www.apple.com",
        description="Consumer technology company.",
    )

    company = create_company(db_session, payload)

    assert company.id is not None
    assert company.ticker == "AAPL"

    fetched = get_company_by_ticker(db_session, "aapl")
    assert fetched is not None
    assert fetched.name == "Apple Inc."

    listed = list_companies(db_session, query="app")
    assert [item.ticker for item in listed] == ["AAPL"]

    updated = update_company(db_session, company, CompanyUpdate(sector="Consumer Technology"))
    assert updated.sector == "Consumer Technology"

    delete_company(db_session, updated)
    assert get_company_by_ticker(db_session, "AAPL") is None


def test_list_companies_without_query_orders_by_ticker(db_session):
    db_session.add_all(
        [
            Company(ticker="MSFT", name="Microsoft Corporation"),
            Company(ticker="AAPL", name="Apple Inc."),
        ]
    )
    db_session.commit()

    companies = list_companies(db_session)

    assert [company.ticker for company in companies] == ["AAPL", "MSFT"]
