from app.db.session import Base, engine
from app.models.alert import Alert
from app.models.alert_automation_rule import AlertAutomationRule
from app.models.alert_notification import AlertNotification
from app.models.company import Company
from app.models.portfolio import Portfolio, PortfolioHolding, PortfolioTransaction
from app.models.research_report import ResearchReport
from app.models.user import User
from app.models.watchlist import Watchlist

_models = (
    User,
    Watchlist,
    Portfolio,
    PortfolioHolding,
    PortfolioTransaction,
    Alert,
    AlertNotification,
    AlertAutomationRule,
    Company,
    ResearchReport,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
