from pathlib import Path


def test_alembic_uses_central_compatibility_loader() -> None:
    env_source = (Path(__file__).resolve().parents[1] / "alembic" / "env.py").read_text()

    assert "_load_compatibility_models()" in env_source
    assert "from app.db.init_db import _active_models, _load_compatibility_models" in env_source

    for legacy_model_name in ("Alert", "Portfolio", "PortfolioHolding", "Watchlist"):
        assert legacy_model_name not in env_source
