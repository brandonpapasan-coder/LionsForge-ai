import importlib.util
import sys
from dataclasses import replace
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release_gates.py"
SPEC = importlib.util.spec_from_file_location("verify_release_gates_result_integrity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

DEFAULT_SHA = "a" * 40


def passing_results():
    runs = []
    for index, (name, path) in enumerate(MODULE.REQUIRED_WORKFLOW_PATHS.items(), start=1):
        runs.append(
            {
                "id": index,
                "run_number": index,
                "run_attempt": 1,
                "name": name,
                "path": path,
                "status": "completed",
                "conclusion": "success",
                "html_url": f"https://example.test/runs/{index}",
                "event": MODULE.REQUIRED_EVENT,
                "head_branch": MODULE.REQUIRED_BRANCH,
                "head_sha": DEFAULT_SHA,
            }
        )
    return MODULE.evaluate_runs(runs, expected_sha=DEFAULT_SHA)


def test_all_passed_rejects_empty_and_partial_results():
    results = passing_results()

    assert not MODULE.all_passed([], expected_sha=DEFAULT_SHA)
    assert not MODULE.all_passed(results[:-1], expected_sha=DEFAULT_SHA)


def test_all_passed_rejects_duplicate_and_unknown_gate_names():
    results = passing_results()
    duplicate = [*results[:-1], results[0]]
    unknown = [*results[:-1], replace(results[-1], name="Unknown Gate")]

    assert not MODULE.all_passed(duplicate, expected_sha=DEFAULT_SHA)
    assert not MODULE.all_passed(unknown, expected_sha=DEFAULT_SHA)


def test_all_passed_rejects_reordered_results():
    results = passing_results()

    assert not MODULE.all_passed(list(reversed(results)), expected_sha=DEFAULT_SHA)


def test_all_passed_rejects_invalid_expected_sha():
    assert not MODULE.all_passed(passing_results(), expected_sha="not-a-sha")


def test_all_passed_rejects_invalid_result_evidence():
    results = passing_results()

    assert not MODULE.all_passed(
        [replace(results[0], run_id=None), *results[1:]],
        expected_sha=DEFAULT_SHA,
    )
    assert not MODULE.all_passed(
        [replace(results[0], run_id=0), *results[1:]],
        expected_sha=DEFAULT_SHA,
    )
    assert not MODULE.all_passed(
        [replace(results[0], path=".github/workflows/wrong.yml"), *results[1:]],
        expected_sha=DEFAULT_SHA,
    )
    assert not MODULE.all_passed(
        [replace(results[0], head_sha="b" * 40), *results[1:]],
        expected_sha=DEFAULT_SHA,
    )


def test_all_passed_accepts_complete_ordered_results():
    assert MODULE.all_passed(passing_results(), expected_sha=DEFAULT_SHA)
