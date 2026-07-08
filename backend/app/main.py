from fastapi import FastAPI
from pydantic import BaseModel

from app.api.router import api_router
from app.core.config import get_settings
from app.db.init_db import init_db

settings = get_settings()


class PlatformInfo(BaseModel):
    name: str
    version: str
    mission: str
    modules: list[str]


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered investment research and trading platform.",
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    if settings.environment in {"development", "test"}:
        init_db()


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "environment": settings.environment,
        "status": "development",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "api": settings.api_prefix,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/platform", response_model=PlatformInfo)
def platform_info():
    return PlatformInfo(
        name=settings.app_name,
        version="0.1.0",
        mission="Deliver AI-assisted investment research, market intelligence, education, and trading workflow tools.",
        modules=[
            "research-assistant",
            "market-news-intelligence",
            "portfolio-watchlists",
            "finance-education",
            "trading-risk-controls",
        ],
    )
