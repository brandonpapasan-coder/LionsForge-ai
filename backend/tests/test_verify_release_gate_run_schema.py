import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release_gates.py"
SPEC = importlib.util.spec_from_file_location("verify_release_gates_run_schema", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


VALID_RUN = {
    "id": 1,
    "run_number": 2,
    "run_attempt": 1,
    "name": "Backend CI",
    "path": ".github/workflows/backend-ci.yml",
    "status": "completed",
    "conclusion": "success",
    "html_url": "https://example.test/runs/1",
    "event": "push",
    "head_branch": "main",
    "head_sha": "a" * 40,
}


def invalid(field, value):
    candidate = dict(VALID_RUN)
    candidate[field] = value
    return candidate


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_number", 0),
        ("run_number", True),
        ("run_number", "2"),
        ("run_attempt", 0),
        ("run_attempt", False),
        ("run_attempt", "1"),
    ],
)
def test_rejects_invalid_ordering_fields(field, value):
    with pytest.raises(RuntimeError, match=field):
        MODULE._validate_page_runs([invalid(field, value)], 1)


@pytest.mark.parametrize(
    "field",
    ["name", "path", "status", "event", "head_branch", "head_sha"],
)
def test_rejects_missing_or_blank_required_strings(field):
    with pytest.raises(RuntimeError, match=field):
        MODULE._validate_page_runs([invalid(field, "")], 2)

    with pytest.raises(RuntimeError, match=field):
        MODULE._validate_page_runs([invalid(field, None)], 2)


def test_rejects_noncanonical_head_sha():
    with pytest.raises(RuntimeError, match="head_sha"):
        MODULE._validate_page_runs([invalid("head_sha", "A" * 40)], 3)

    with pytest.raises(RuntimeError, match="head_sha"):
        MODULE._validate_page_runs([invalid("head_sha", "a" * 39)], 3)


@pytest.mark.parametrize("field", ["conclusion", "html_url"])
def test_rejects_invalid_optional_string_values(field):
    with pytest.raises(RuntimeError, match=field):
        MODULE._validate_page_runs([invalid(field, "")], 4)

    with pytest.raises(RuntimeError, match=field):
        MODULE._validate_page_runs([invalid(field, 7)], 4)


def test_accepts_null_optional_fields_for_incomplete_runs():
    candidate = dict(VALID_RUN)
    candidate["status"] = "in_progress"
    candidate["conclusion"] = None
    candidate["html_url"] = None

    validated = MODULE._validate_page_runs([candidate], 5)

    assert validated[0]["conclusion"] is None
    assert validated[0]["html_url"] is None


def test_validated_ordering_fields_drive_deterministic_selection():
    older = dict(VALID_RUN)
    newer = dict(VALID_RUN)
    older.update({"id": 10, "run_number": 4, "run_attempt": 1})
    newer.update({"id": 11, "run_number": 4, "run_attempt": 2})

    runs = MODULE._validate_page_runs([older, newer], 6)
    result = next(
        gate
        for gate in MODULE.evaluate_runs(runs, expected_sha="a" * 40)
        if gate.name == "Backend CI"
    )

    assert result.run_id == 11
