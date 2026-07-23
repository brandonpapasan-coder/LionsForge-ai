import importlib.util
import io
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release_gates.py"
SPEC = importlib.util.spec_from_file_location("verify_release_gates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

DEFAULT_SHA = "a" * 40


class FakeHeaders:
    def __init__(self, content_type="application/json"):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type

    def get(self, name, default=None):
        return default


class FakeResponse(io.BytesIO):
    def __init__(self, body, content_type="application/json"):
        super().__init__(body)
        self.headers = FakeHeaders(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


def run(
    name,
    *,
    status="completed",
    conclusion="success",
    run_number=1,
    run_attempt=1,
    run_id=1,
    event="push",
    head_branch="main",
    head_sha=DEFAULT_SHA,
    path=None,
):
    return {
        "name": name,
        "path": path or MODULE.REQUIRED_WORKFLOW_PATHS[name],
        "status": status,
        "conclusion": conclusion,
        "run_number": run_number,
        "run_attempt": run_attempt,
        "id": run_id,
        "html_url": f"https://example.test/runs/{run_id}",
        "event": event,
        "head_branch": head_branch,
        "head_sha": head_sha,
    }


def test_all_required_main_push_workflows_pass():
    runs = [
        run(name, run_id=index) for index, name in enumerate(MODULE.REQUIRED_WORKFLOWS, start=1)
    ]
    results = MODULE.evaluate_runs(runs)
    assert MODULE.all_passed(results)


def test_all_required_exact_sha_workflows_pass():
    runs = [
        run(name, run_id=index) for index, name in enumerate(MODULE.REQUIRED_WORKFLOWS, start=1)
    ]
    results = MODULE.evaluate_runs(runs, expected_sha=DEFAULT_SHA)
    assert MODULE.all_passed(results, expected_sha=DEFAULT_SHA)
    assert {result.head_sha for result in results} == {DEFAULT_SHA}
    assert {result.path for result in results} == set(MODULE.REQUIRED_WORKFLOW_PATHS.values())


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


def test_latest_rerun_attempt_wins_for_same_run_number():
    runs = [
        run(
            "Backend CI",
            conclusion="failure",
            run_number=5,
            run_attempt=1,
            run_id=50,
        ),
        run(
            "Backend CI",
            conclusion="success",
            run_number=5,
            run_attempt=2,
            run_id=51,
        ),
    ]
    backend = next(result for result in MODULE.evaluate_runs(runs) if result.name == "Backend CI")
    assert backend.run_id == 51
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


def test_wrong_head_sha_does_not_satisfy_gate():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run("Backend CI", head_sha="b" * 40)
    results = MODULE.evaluate_runs(runs, expected_sha=DEFAULT_SHA)
    backend = next(result for result in results if result.name == "Backend CI")
    assert backend.status == "missing"
    assert backend.head_sha is None
    assert not MODULE.all_passed(results, expected_sha=DEFAULT_SHA)


def test_spoofed_workflow_name_with_wrong_path_does_not_satisfy_gate():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run(
        "Backend CI",
        path=".github/workflows/spoofed-backend-ci.yml",
    )
    results = MODULE.evaluate_runs(runs, expected_sha=DEFAULT_SHA)
    backend = next(result for result in results if result.name == "Backend CI")
    assert backend.status == "missing"
    assert backend.path == MODULE.REQUIRED_WORKFLOW_PATHS["Backend CI"]
    assert not MODULE.all_passed(results, expected_sha=DEFAULT_SHA)


def test_all_passed_rechecks_recorded_head_sha():
    results = MODULE.evaluate_runs(
        [run(name) for name in MODULE.REQUIRED_WORKFLOWS],
        expected_sha=DEFAULT_SHA,
    )
    assert not MODULE.all_passed(results, expected_sha="b" * 40)


def test_in_progress_or_failed_gate_fails():
    runs = [run(name) for name in MODULE.REQUIRED_WORKFLOWS]
    runs[0] = run("Backend CI", status="in_progress", conclusion=None)
    assert not MODULE.all_passed(MODULE.evaluate_runs(runs))
    runs[0] = run("Backend CI", conclusion="failure")
    assert not MODULE.all_passed(MODULE.evaluate_runs(runs))


def test_input_validation_rejects_malformed_repository_and_sha():
    with pytest.raises(ValueError, match="owner/name"):
        MODULE.validate_inputs("not-a-repository", "a" * 40)
    with pytest.raises(ValueError, match="40 lowercase"):
        MODULE.validate_inputs("owner/repository", "ABC123")


def test_validate_page_runs_rejects_malformed_entries_and_ids():
    with pytest.raises(RuntimeError, match="non-object run"):
        MODULE._validate_page_runs(["not-an-object"], 1)
    with pytest.raises(RuntimeError, match="invalid run id"):
        MODULE._validate_page_runs([{"id": 0}], 1)
    with pytest.raises(RuntimeError, match="invalid run id"):
        MODULE._validate_page_runs([{"id": True}], 1)


def test_validate_page_runs_rejects_duplicate_ids_within_page():
    duplicate_runs = [
        run("Backend CI", run_id=7),
        run("Frontend CI", run_id=7),
    ]
    with pytest.raises(RuntimeError, match="duplicate run id 7"):
        MODULE._validate_page_runs(duplicate_runs, 2)


def test_response_media_type_requires_readable_json_headers():
    with pytest.raises(RuntimeError, match="did not include headers"):
        MODULE._response_media_type(object())
    response = FakeResponse(b"{}", content_type="text/html")
    with pytest.raises(RuntimeError, match="unexpected content type: text/html"):
        MODULE._response_media_type(response)


def test_fetch_page_rejects_malformed_json(monkeypatch):
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: FakeResponse(b"{"))
    with pytest.raises(RuntimeError, match="returned malformed JSON"):
        MODULE._fetch_page("owner/repository", DEFAULT_SHA, "token", 1)


def test_fetch_page_rejects_timeout(monkeypatch):
    def raise_timeout(request, timeout):
        raise TimeoutError("timed out")
    monkeypatch.setattr(MODULE, "urlopen", raise_timeout)
    with pytest.raises(RuntimeError, match="request failed: timed out"):
        MODULE._fetch_page("owner/repository", DEFAULT_SHA, "token", 1)


def test_fetch_page_rejects_incomplete_read(monkeypatch):
    def raise_incomplete_read(request, timeout):
        raise MODULE.IncompleteRead(b"partial", 100)
    monkeypatch.setattr(MODULE, "urlopen", raise_incomplete_read)
    with pytest.raises(RuntimeError, match="request failed"):
        MODULE._fetch_page("owner/repository", DEFAULT_SHA, "token", 1)


def test_fetch_runs_paginates_until_partial_page(monkeypatch):
    first_page = [run("Backend CI", run_id=index) for index in range(1, MODULE.PER_PAGE + 1)]
    second_page = [run("Frontend CI", run_id=1000)]
    requested_pages = []
    def fake_fetch_page(repository, sha, token, page):
        assert repository == "owner/repository"
        assert sha == DEFAULT_SHA
        assert token == "token"
        requested_pages.append(page)
        return first_page if page == 1 else second_page
    monkeypatch.setattr(MODULE, "_fetch_page", fake_fetch_page)
    runs = MODULE.fetch_runs("owner/repository", DEFAULT_SHA, "token")
    assert requested_pages == [1, 2]
    assert runs == first_page + second_page


def test_fetch_runs_rejects_repeated_ids_across_pages(monkeypatch):
    monkeypatch.setattr(MODULE, "PER_PAGE", 2)
    pages = {
        1: [run("Backend CI", run_id=1), run("Frontend CI", run_id=2)],
        2: [run("Security Gate", run_id=2)],
    }
    monkeypatch.setattr(
        MODULE,
        "_fetch_page",
        lambda repository, sha, token, page: pages[page],
    )
    with pytest.raises(RuntimeError, match="repeated run id.*2"):
        MODULE.fetch_runs("owner/repository", DEFAULT_SHA, "token")


def test_fetch_runs_enforces_maximum_page_limit(monkeypatch):
    monkeypatch.setattr(MODULE, "PER_PAGE", 1)
    monkeypatch.setattr(MODULE, "MAX_PAGES", 2)
    monkeypatch.setattr(
        MODULE,
        "_fetch_page",
        lambda repository, sha, token, page: [run("Backend CI", run_id=page)],
    )
    with pytest.raises(RuntimeError, match="2-page safety limit"):
        MODULE.fetch_runs("owner/repository", DEFAULT_SHA, "token")
