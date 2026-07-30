from app.internal_alpha.feedback_pipeline import AlphaFeedback, validate_feedback


def build(**changes: object) -> AlphaFeedback:
    values: dict[str, object] = {
        "feedback_id": "feedback_0001",
        "experiment_id": "experiment_0001",
        "severity": "HIGH",
        "category": "DEFECT",
        "reproducibility": "ALWAYS",
        "reason_codes": ("incorrect_output",),
    }
    values.update(changes)
    return AlphaFeedback(**values)  # type: ignore[arg-type]


def test_accepts_structured_privacy_safe_feedback() -> None:
    assert validate_feedback(build())


def test_rejects_malformed_ids_and_unknown_enums() -> None:
    assert not validate_feedback(build(feedback_id="bad"))
    assert not validate_feedback(build(experiment_id="bad"))
    assert not validate_feedback(build(severity="URGENT"))
    assert not validate_feedback(build(category="OTHER"))
    assert not validate_feedback(build(reproducibility="MAYBE"))


def test_rejects_empty_duplicate_and_malformed_reason_codes() -> None:
    assert not validate_feedback(build(reason_codes=()))
    assert not validate_feedback(build(reason_codes=("incorrect_output", "incorrect_output")))
    assert not validate_feedback(build(reason_codes=("bad",)))


def test_reserves_critical_severity_for_defects() -> None:
    assert validate_feedback(build(severity="CRITICAL", category="DEFECT"))
    assert not validate_feedback(build(severity="CRITICAL", category="USABILITY"))
