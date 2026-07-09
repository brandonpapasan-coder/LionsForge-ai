from fastapi import APIRouter

from app.api.routes import alerts, auth, companies, factors, market, news, portfolios, research, watchlists

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(factors.router, prefix="/factors", tags=["factors"])
