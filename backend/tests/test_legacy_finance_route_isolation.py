from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import Settings

LEGACY_PREFIXES = (
    "/api/v1/market",
    "/api/v1/market-simulator",
    "/api/v1/watchlists",
    "/api/v1/portfolios",
    "/api/v1/alerts",
    "/api/v1/advanced-alerts",
    "/api/v1/companies",
    "/api/v1/factors",
    "/api/v1/events",
    "/api/v1/decisions",
)

CORE_PREFIXES = (
    "/api/v1/research-projects",
    "/api/v1/research-packet-integrity",
    "/api/v1/education",
    "/api/v1/mentor",
    "/api/v1/system",
)


def openapi_paths(*, enabled: bool) -> set[str]:
    settings = Settings(
        _env_file=None,
        enable_legacy_finance_modules=enabled,
    )
    app = FastAPI()
    app.include_router(build_api_router(settings), prefix="/api/v1")
    return set(app.openapi()["paths"])


def test_legacy_finance_routes_are_disabled_by_default():
    settings = Settings(_env_file=None, enable_legacy_finance_modules=False)
    assert settings.enable_legacy_finance_modules is False

    paths = openapi_paths(enabled=False)
    assert all(
        not path.startswith(prefix)
        for path in paths
        for prefix in LEGACY_PREFIXES
    )


def test_core_research_routes_remain_available_when_legacy_routes_are_disabled():
    paths = openapi_paths(enabled=False)

    for prefix in CORE_PREFIXES:
        assert any(path.startswith(prefix) for path in paths)


def test_legacy_finance_routes_require_explicit_opt_in():
    paths = openapi_paths(enabled=True)

    for prefix in LEGACY_PREFIXES:
        assert any(path.startswith(prefix) for path in paths)
