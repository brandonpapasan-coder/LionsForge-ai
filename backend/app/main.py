from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.api.router import api_router
from app.core.config import get_settings
from app.core.observability import configure_request_observability
from app.db.init_db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.environment in {"development", "test"}:
        init_db()
    yield


class PlatformInfo(BaseModel):
    name: str
    version: str
    mission: str
    modules: list[str]


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered research, validation, and education platform.",
    lifespan=lifespan,
)
configure_request_observability(app)
app.include_router(api_router, prefix=settings.api_prefix)


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
        mission="Deliver AI-assisted research, evidence validation, and adaptive education.",
        modules=[
            "research-assistant",
            "evidence-validation",
            "market-news-intelligence",
            "portfolio-risk-intelligence",
            "adaptive-education",
        ],
    )
