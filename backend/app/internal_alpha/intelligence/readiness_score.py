"""Internal alpha readiness scoring primitives."""


def calculate_readiness_score(*, security: float, reliability: float, feedback: float, regression: float) -> float:
    values = [security, reliability, feedback, regression]
    if any(value < 0 or value > 100 for value in values):
        raise ValueError("scores must be between 0 and 100")
    return round(sum(values) / len(values), 2)
