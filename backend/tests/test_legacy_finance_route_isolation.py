from app.api.router import build_api_router
from app.core.config import Settings

LEGACY_PREFIXES = (
    "/market",
    "/market-simulator",
    "/watchlists",
    "/portfolios",
    "/alerts",
    "/advanced-alerts",
    "/companies",
    "/factors",
    "/events",
    "/decisions",
)


def route_paths(*, enabled: bool) -> set[str]:
    settings = Settings(
        _env_file=None,
        enable_legacy_finance_modules=enabled,
    )
    return {
        path
        for route in build_api_router(settings).routes
        if isinstance((path := getattr(route, "path", None)), str)
    }


def test_legacy_finance_routes_are_disabled_by_default():
    settings = Settings(_env_file=None, enable_legacy_finance_modules=False)
    assert settings.enable_legacy_finance_modules is False

    paths = route_paths(enabled=False)
    assert all(
        not path.startswith(prefix)
        for path in paths
        for prefix in LEGACY_PREFIXES
    )


def test_core_research_routes_remain_available_when_legacy_routes_are_disabled():
    paths = route_paths(enabled=False)

    assert any(path.startswith("/research-projects") for path in paths)
    assert any(path.startswith("/research-packet-integrity") for path in paths)
    assert any(path.startswith("/education") for path in paths)
    assert any(path.startswith("/mentor") for path in paths)
    assert any(path.startswith("/system") for path in paths)


def test_legacy_finance_routes_require_explicit_opt_in():
    paths = route_paths(enabled=True)

    for prefix in LEGACY_PREFIXES:
        assert any(path.startswith(prefix) for path in paths)
