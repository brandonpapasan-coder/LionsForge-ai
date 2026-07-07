from fastapi import FastAPI
from pydantic import BaseModel


class PlatformInfo(BaseModel):
    name: str
    version: str
    mission: str
    modules: list[str]


app = FastAPI(
    title="LionsForge AI",
    version="0.1.0",
    description="AI-powered investment research and trading platform.",
)


@app.get("/")
def root():
    return {
        "name": "LionsForge AI",
        "status": "development",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
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
        name="LionsForge AI",
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
