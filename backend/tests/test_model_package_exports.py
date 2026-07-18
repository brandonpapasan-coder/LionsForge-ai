import json
import subprocess
import sys


def _run_model_import_probe(script: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_active_model_import_does_not_load_legacy_modules() -> None:
    result = _run_model_import_probe(
        """
import json
import sys
from app.models import ResearchSession

legacy_modules = [
    "app.models.alert",
    "app.models.market_simulator",
    "app.models.portfolio",
    "app.models.watchlist",
]
print(json.dumps({
    "research_session_module": ResearchSession.__module__,
    "loaded_legacy_modules": [name for name in legacy_modules if name in sys.modules],
}))
"""
    )

    assert result == {
        "research_session_module": "app.models.research_session",
        "loaded_legacy_modules": [],
    }


def test_legacy_model_exports_remain_compatible() -> None:
    result = _run_model_import_probe(
        """
import json
from app.models import (
    Alert,
    MarketLearningSession,
    Portfolio,
    PortfolioHolding,
    SimulatedTrade,
    SimulationAccount,
    VirtualPosition,
    Watchlist,
)

print(json.dumps({
    "Alert": Alert.__module__,
    "MarketLearningSession": MarketLearningSession.__module__,
    "Portfolio": Portfolio.__module__,
    "PortfolioHolding": PortfolioHolding.__module__,
    "SimulatedTrade": SimulatedTrade.__module__,
    "SimulationAccount": SimulationAccount.__module__,
    "VirtualPosition": VirtualPosition.__module__,
    "Watchlist": Watchlist.__module__,
}))
"""
    )

    assert result == {
        "Alert": "app.models.alert",
        "MarketLearningSession": "app.models.market_simulator",
        "Portfolio": "app.models.portfolio",
        "PortfolioHolding": "app.models.portfolio",
        "SimulatedTrade": "app.models.market_simulator",
        "SimulationAccount": "app.models.market_simulator",
        "VirtualPosition": "app.models.market_simulator",
        "Watchlist": "app.models.watchlist",
    }
