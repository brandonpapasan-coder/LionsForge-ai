from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

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


class LaunchGate(BaseModel):
    key: str
    category: Literal["repository", "external"]
    status: Literal["available", "unverified"]
    issue: int | None = None


class LaunchReadiness(BaseModel):
    contract_version: str
    release_candidate: str
    overall_status: Literal["blocked_external_evidence"]
    gates: list[LaunchGate]
    interpretation_notice: str


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


@app.get("/launch-readiness", response_model=LaunchReadiness)
def launch_readiness():
    return LaunchReadiness(
        contract_version="1.0",
        release_candidate="8488db1545d6053edc1c0cebc4c74ac93b64bf7b",
        overall_status="blocked_external_evidence",
        gates=[
            LaunchGate(key="repository_validation_controls", category="repository", status="available"),
            LaunchGate(key="staging_acceptance", category="external", status="unverified", issue=29),
            LaunchGate(key="production_controls", category="external", status="unverified", issue=401),
            LaunchGate(key="policy_and_support", category="external", status="unverified", issue=402),
            LaunchGate(key="controlled_beta", category="external", status="unverified", issue=403),
            LaunchGate(key="general_availability", category="external", status="unverified", issue=400),
        ],
        interpretation_notice=(
            "Repository controls and passing workflows are not proof that a live environment, "
            "policy approval, controlled beta, or general-availability acceptance has completed."
        ),
    )
