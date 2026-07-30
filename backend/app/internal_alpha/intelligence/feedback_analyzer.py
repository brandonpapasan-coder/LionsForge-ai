"""Privacy-safe deterministic internal-alpha feedback analysis."""

from collections import Counter
from collections.abc import Iterable, Mapping


VALID_CATEGORIES = {
    "DEFECT",
    "USABILITY",
    "RESEARCH_QUALITY",
    "PERFORMANCE",
    "ACCESSIBILITY",
}
_MAX_ITEMS = 10_000


def summarize_categories(feedback_items: Iterable[Mapping[str, object]]) -> dict[str, int]:
    """Count controlled categories without retaining free-form feedback data."""
    counts: Counter[str] = Counter()
    for index, item in enumerate(feedback_items):
        if index >= _MAX_ITEMS:
            raise ValueError("feedback input exceeds bounded analysis limit")
        category = item.get("category")
        if not isinstance(category, str) or category not in VALID_CATEGORIES:
            raise ValueError("feedback contains an invalid category")
        counts[category] += 1
    return dict(sorted(counts.items()))


def find_repeated_categories(
    feedback_items: Iterable[Mapping[str, object]], minimum: int = 2
) -> dict[str, int]:
    if isinstance(minimum, bool) or not isinstance(minimum, int):
        raise TypeError("minimum must be an integer")
    if not 2 <= minimum <= _MAX_ITEMS:
        raise ValueError("minimum must be between 2 and the analysis limit")
    summary = summarize_categories(feedback_items)
    return {key: value for key, value in summary.items() if value >= minimum}
