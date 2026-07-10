from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.dependency_health import evaluate_market_dependencies
from app.core.metrics import render_prometheus_metrics
from app.core.observability import configure_request_observability
from app.core.rate_limit import configure_rate_limiting
from app.db.init_db import init_db
from app.db.session import get_db
from app.services.market_provider_health import provider_health_registry

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
    description="AI-powered investment research and trading platform.",
    lifespan=lifespan,
)
configure_request_observability(app)
configure_rate_limiting(app, settings)
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
        "metrics": "/metrics",
        "api": settings.api_prefix,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database dependency is unavailable.",
        ) from exc

    market = evaluate_market_dependencies(settings, provider_health_registry)
    payload = {
        "status": "ready" if market.status == "available" else market.status,
        "database": "available",
        "market_data": market.status,
        "primary_provider": market.primary_provider,
        "unavailable_providers": list(market.unavailable_providers),
    }
    if market.status == "unavailable":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )
    return payload


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(
        render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/platform", response_model=PlatformInfo)
def platform_info():
    return PlatformInfo(
        name=settings.app_name,
        version="0.1.0",
        mission=(
            "Deliver AI-assisted investment research, market intelligence, "
            "education, and trading workflow tools."
        ),
        modules=[
            "research-assistant",
            "market-news-intelligence",
            "portfolio-watchlists",
            "finance-education",
            "trading-risk-controls",
        ],
    )
