import os
import subprocess
import sys
import textwrap
from pathlib import Path

from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import Settings
from app.core.legacy_finance_config import LegacyFinanceSettings

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

LEGACY_MODULES = (
    "app.api.routes.advanced_alerts",
    "app.api.routes.alerts",
    "app.api.routes.autonomous_portfolios",
    "app.api.routes.companies",
    "app.api.routes.decisions",
    "app.api.routes.events",
    "app.api.routes.factors",
    "app.api.routes.market",
    "app.api.routes.market_learning",
    "app.api.routes.market_learning_evidence",
    "app.api.routes.market_learning_mastery",
    "app.api.routes.market_learning_portfolio",
    "app.api.routes.market_learning_progress",
    "app.api.routes.market_learning_roadmap",
    "app.api.routes.market_mentor",
    "app.api.routes.market_simulator",
    "app.api.routes.portfolios",
    "app.api.routes.watchlists",
)

CORE_PREFIXES = (
    "/api/v1/research-projects",
    "/api/v1/research-packet-integrity",
    "/api/v1/education",
    "/api/v1/mentor",
    "/api/v1/system",
)


def openapi_paths(*, enabled: bool) -> set[str]:
    settings = Settings(_env_file=None)
    legacy_finance_settings = LegacyFinanceSettings(
        _env_file=None,
        enable_legacy_finance_modules=enabled,
    )
    app = FastAPI()
    app.include_router(
        build_api_router(settings, legacy_finance_settings),
        prefix="/api/v1",
    )
    return set(app.openapi()["paths"])


def test_legacy_finance_routes_are_disabled_by_default():
    settings = LegacyFinanceSettings(_env_file=None)
    assert settings.enable_legacy_finance_modules is False

    paths = openapi_paths(enabled=False)
    assert all(
        not path.startswith(prefix)
        for path in paths
        for prefix in LEGACY_PREFIXES
    )


def test_disabled_startup_does_not_import_legacy_finance_modules():
    script = textwrap.dedent(
        f"""
        import sys
        import app.api.router  # noqa: F401

        legacy_modules = {LEGACY_MODULES!r}
        imported = [name for name in legacy_modules if name in sys.modules]
        if imported:
            raise SystemExit(f"legacy modules imported: {{imported}}")
        """
    )
    env = os.environ.copy()
    env.pop("ENABLE_LEGACY_FINANCE_MODULES", None)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_core_research_routes_remain_available_when_legacy_routes_are_disabled():
    paths = openapi_paths(enabled=False)

    for prefix in CORE_PREFIXES:
        assert any(path.startswith(prefix) for path in paths)


def test_legacy_finance_routes_require_explicit_opt_in():
    paths = openapi_paths(enabled=True)

    for prefix in LEGACY_PREFIXES:
        assert any(path.startswith(prefix) for path in paths)
