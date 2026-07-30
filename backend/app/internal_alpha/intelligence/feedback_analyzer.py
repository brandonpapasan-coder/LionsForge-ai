"""Internal alpha feedback analysis primitives."""

from collections import Counter


def summarize_categories(feedback_items: list[dict]) -> dict[str, int]:
    categories = [item.get("category", "unknown") for item in feedback_items]
    return dict(Counter(categories))


def find_repeated_categories(feedback_items: list[dict], minimum: int = 2) -> dict[str, int]:
    summary = summarize_categories(feedback_items)
    return {key: value for key, value in summary.items() if value >= minimum}
