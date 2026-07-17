from app.api.router import build_api_router
from app.core.config import Settings

LEGACY_TAGS = {
    "market",
    "market-simulator",
    "market-simulator-mentor",
    "market-simulator-learning",
    "watchlists",
    "portfolios",
    "portfolio-intelligence",
    "alerts",
    "advanced-alerts",
    "companies",
    "factors",
    "events",
    "decisions",
}

CORE_TAGS = {
    "research-projects",
    "research-packet-integrity",
    "education",
    "mentor",
    "system",
}


def route_tags(*, enabled: bool) -> set[str]:
    settings = Settings(
        _env_file=None,
        enable_legacy_finance_modules=enabled,
    )
    return {
        tag
        for route in build_api_router(settings).routes
        for tag in getattr(route, "tags", [])
        if isinstance(tag, str)
    }


def test_legacy_finance_routes_are_disabled_by_default():
    settings = Settings(_env_file=None, enable_legacy_finance_modules=False)
    assert settings.enable_legacy_finance_modules is False

    tags = route_tags(enabled=False)
    assert tags.isdisjoint(LEGACY_TAGS)


def test_core_research_routes_remain_available_when_legacy_routes_are_disabled():
    tags = route_tags(enabled=False)
    assert CORE_TAGS <= tags


def test_legacy_finance_routes_require_explicit_opt_in():
    tags = route_tags(enabled=True)
    assert LEGACY_TAGS <= tags
