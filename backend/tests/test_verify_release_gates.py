import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release_gates.py"
SPEC = importlib.util.spec_from_file_location("verify_release_gates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run(
    name,
    *,
    status="completed",
    conclusion="success",
    run_number=1,
    run_id=1,
    event="push",
    head_branch="main",
):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_number": run_number,
        "id": run_id,
        "html_url": f"https://example.test/runs/{run_id}",
        "event": event,
        "head_branch": head_branch,
    }


def test_all_required_main_push_workflows_pass():
    runs = [
        run(name, run_id=index)
        for index, name in enumerate(MODULE.REQUIRED_WORKFLOWS, start=1)
    ]
    results = MODULE.evaluate_runs(runs)
    assert MODULE.all_passed(results)


def test_missing_required_workflow_fails():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS[:-1]]
    results = MODULE.evaluate_runs(runs)
    assert not MODULE.all_passed(results)
    assert results[-1].status == "missing"


def test_latest_eligible_run_wins():
    runs = [
        run("Backend CI", conclusion="failure", run_number=1, run_id=10),
        run("Backend CI", conclusion="success", run_number=2, run_id=11),
    ]
    results = MODULE.evaluate_runs(runs)
    backend = next(result for result in results if result.name == "Backend CI")
    assert backend.run_id == 11
    assert backend.conclusion == "success"


def test_newer_manual_run_does_not_replace_main_push_evidence():
    runs = [
        run("Backend CI", conclusion="success", run_number=2, run_id=20),
        run(
            "Backend CI",
            conclusion="success",
            run_number=3,
            run_id=21,
            event="workflow_dispatch",
        ),
    ]
    results = MODULE.evaluate_runs(runs)
    backend = next(result for result in results if result.name == "Backend CI")
    assert backend.run_id == 20
    assert backend.event == "push"


def test_non_main_push_does_not_satisfy_gate():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run("Backend CI", head_branch="dev/example")
    results = MODULE.evaluate_runs(runs)
    backend = next(result for result in results if result.name == "Backend CI")
    assert backend.status == "missing"
    assert not MODULE.all_passed(results)


def test_pull_request_run_does_not_satisfy_gate():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run("Backend CI", event="pull_request")
    assert not MODULE.all_passed(MODULE.evaluate_runs(runs))


def test_in_progress_or_failed_gate_fails():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run("Backend CI", status="in_progress", conclusion=None)
    assert not MODULE.all_passed(MODULE.evaluate_runs(runs))

    runs[0] = run("Backend CI", conclusion="failure")
    assert not MODULE.all_passed(MODULE.evaluate_runs(runs))