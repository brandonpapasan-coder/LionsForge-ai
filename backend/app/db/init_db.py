from app.db.session import Base, engine
from app.models.user import User
from app.models.watchlist import Watchlist

_models = (User, Watchlist)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
