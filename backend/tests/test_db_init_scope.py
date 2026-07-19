import json
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LEGACY_MODULES = {
    "app.models.alert",
    "app.models.alert_automation_rule",
    "app.models.alert_notification",
    "app.models.market_simulator",
    "app.models.portfolio",
    "app.models.research_report",
    "app.models.watchlist",
}


def _loaded_modules(code: str) -> set[str]:
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(json.loads(result.stdout))


def test_importing_db_initializer_keeps_legacy_models_unloaded() -> None:
    loaded = _loaded_modules(
        "import json, sys; import app.db.init_db; "
        "print(json.dumps(sorted(name for name in sys.modules if name.startswith('app.models.'))))"
    )

    assert loaded.isdisjoint(LEGACY_MODULES)


def test_compatibility_loader_registers_legacy_model_modules() -> None:
    loaded = _loaded_modules(
        "import json, sys; from app.db.init_db import _load_compatibility_models; "
        "_load_compatibility_models(); "
        "print(json.dumps(sorted(name for name in sys.modules if name.startswith('app.models.'))))"
    )

    assert LEGACY_MODULES.issubset(loaded)
