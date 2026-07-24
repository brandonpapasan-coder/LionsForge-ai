from pathlib import Path

from app.core.config import Settings


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_product_name_is_onyxmane_intelligence():
    assert Settings().app_name == "Onyxmane Intelligence"


def test_primary_user_facing_surfaces_use_canonical_brand():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    layout = (ROOT / "frontend" / "app" / "layout.tsx").read_text(encoding="utf-8")

    assert readme.startswith("# Onyxmane Intelligence\n")
    assert 'title: "Onyxmane Intelligence"' in layout
    assert "LionsForge AI" not in readme
    assert 'title: "LionsForge AI"' not in layout
