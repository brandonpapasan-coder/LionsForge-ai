import pytest

from app.internal_alpha.intelligence.feedback_analyzer import (
    find_repeated_categories,
    summarize_categories,
)


def test_summarizes_categories_deterministically() -> None:
    items = [
        {"category": "USABILITY"},
        {"category": "DEFECT"},
        {"category": "USABILITY"},
    ]
    assert summarize_categories(items) == {"DEFECT": 1, "USABILITY": 2}
    assert find_repeated_categories(items) == {"USABILITY": 2}


def test_rejects_unknown_or_missing_categories() -> None:
    with pytest.raises(ValueError):
        summarize_categories([{"category": "OTHER"}])
    with pytest.raises(ValueError):
        summarize_categories([{}])


@pytest.mark.parametrize("minimum", [0, 1, 10_001])
def test_rejects_invalid_repeat_threshold(minimum: int) -> None:
    with pytest.raises(ValueError):
        find_repeated_categories([], minimum=minimum)


def test_rejects_boolean_repeat_threshold() -> None:
    with pytest.raises(TypeError):
        find_repeated_categories([], minimum=True)
