from fastapi import APIRouter

from app.api.routes import news, research, watchlists

api_router = APIRouter()
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
