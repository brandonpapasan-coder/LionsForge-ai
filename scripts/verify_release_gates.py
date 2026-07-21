#!/usr/bin/env python3
"""Verify required GitHub Actions workflows succeeded for an exact commit SHA."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from http.client import IncompleteRead
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REQUIRED_WORKFLOW_PATHS = {
    "Backend CI": ".github/workflows/backend-ci.yml",
    "Frontend CI": ".github/workflows/frontend-ci.yml",
    "Security Gate": ".github/workflows/security-gate.yml",
    "Deployment Validation": ".github/workflows/deployment-validation.yml",
}
REQUIRED_WORKFLOWS = tuple(REQUIRED_WORKFLOW_PATHS)
REQUIRED_EVENT = "push"
REQUIRED_BRANCH = "main"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PER_PAGE = 100
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
EXPECTED_MEDIA_TYPES = {"application/json", "application/vnd.github+json"}


@dataclass(frozen=True)
class GateResult:
    name: str
    path: str | None
    status: str
    conclusion: str | None
    run_id: int | None
    html_url: str | None
    event: str | None
    head_branch: str | None
    head_sha: str | None


def validate_inputs(repository: str, sha: str) -> None:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository must use owner/name format")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("sha must be exactly 40 lowercase hexadecimal characters")


def is_eligible_run(
    run: dict,
    expected_sha: str | None = None,
    expected_path: str | None = None,
) -> bool:
    if run.get("event") != REQUIRED_EVENT or run.get("head_branch") != REQUIRED_BRANCH:
        return False
    if expected_sha is not None and run.get("head_sha") != expected_sha:
        return False
    return expected_path is None or run.get("path") == expected_path


def evaluate_runs(
    runs: list[dict], expected_sha: str | None = None
) -> list[GateResult]:
    results: list[GateResult] = []
    for workflow_name, workflow_path in REQUIRED_WORKFLOW_PATHS.items():
        matches = [
            run
            for run in runs
            if run["name"] == workflow_name
            and is_eligible_run(
                run,
                expected_sha=expected_sha,
                expected_path=workflow_path,
            )
        ]
        matches.sort(
            key=lambda run: (run["run_number"], run["run_attempt"], run["id"]),
            reverse=True,
        )
        if not matches:
            results.append(
                GateResult(
                    workflow_name,
                    workflow_path,
                    "missing",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )
            continue
        run = matches[0]
        results.append(
            GateResult(
                workflow_name,
                run["path"],
                run["status"],
                run["conclusion"],
                run["id"],
                run["html_url"],
                run["event"],
                run["head_branch"],
                run["head_sha"],
            )
        )
    return results


def all_passed(
    results: list[GateResult], expected_sha: str | None = None
) -> bool:
    if expected_sha is not None and not SHA_RE.fullmatch(expected_sha):
        return False
    if len(results) != len(REQUIRED_WORKFLOWS):
        return False

    results_by_name: dict[str, GateResult] = {}
    for result in results:
        if result.name not in REQUIRED_WORKFLOW_PATHS or result.name in results_by_name:
            return False
        results_by_name[result.name] = result

    if tuple(results_by_name) != REQUIRED_WORKFLOWS:
        return False

    for workflow_name, workflow_path in REQUIRED_WORKFLOW_PATHS.items():
        result = results_by_name[workflow_name]
        if not (
            result.path == workflow_path
            and result.status == "completed"
            and result.conclusion == "success"
            and result.run_id is not None
            and result.run_id > 0
            and result.event == REQUIRED_EVENT
            and result.head_branch == REQUIRED_BRANCH
            and isinstance(result.head_sha, str)
            and SHA_RE.fullmatch(result.head_sha)
            and (expected_sha is None or result.head_sha == expected_sha)
        ):
            return False
    return True


def _positive_int(value: object, field: str, page: int, index: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RuntimeError(
            f"GitHub Actions API page {page} contained an invalid {field} at index {index}"
        )
    return value


def _required_string(value: object, field: str, page: int, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"GitHub Actions API page {page} contained an invalid {field} at index {index}"
        )
    return value


def _optional_string(
    value: object, field: str, page: int, index: int
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"GitHub Actions API page {page} contained an invalid {field} at index {index}"
        )
    return value


def _validate_run(run: dict, page: int, index: int) -> dict:
    run_id = _positive_int(run.get("id"), "run id", page, index)
    run_number = _positive_int(run.get("run_number"), "run_number", page, index)
    run_attempt = _positive_int(run.get("run_attempt"), "run_attempt", page, index)
    name = _required_string(run.get("name"), "name", page, index)
    path = _required_string(run.get("path"), "path", page, index)
    status = _required_string(run.get("status"), "status", page, index)
    event = _required_string(run.get("event"), "event", page, index)
    head_branch = _required_string(run.get("head_branch"), "head_branch", page, index)
    head_sha = _required_string(run.get("head_sha"), "head_sha", page, index)
    if not SHA_RE.fullmatch(head_sha):
        raise RuntimeError(
            f"GitHub Actions API page {page} contained an invalid head_sha at index {index}"
        )
    conclusion = _optional_string(run.get("conclusion"), "conclusion", page, index)
    html_url = _optional_string(run.get("html_url"), "html_url", page, index)
    return {
        **run,
        "id": run_id,
        "run_number": run_number,
        "run_attempt": run_attempt,
        "name": name,
        "path": path,
        "status": status,
        "event": event,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "conclusion": conclusion,
        "html_url": html_url,
    }


def _validate_page_runs(runs: object, page: int) -> list[dict]:
    if not isinstance(runs, list):
        raise RuntimeError("GitHub Actions API response did not contain workflow_runs")

    validated: list[dict] = []
    page_run_ids: set[int] = set()
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            raise RuntimeError(
                f"GitHub Actions API page {page} contained a non-object run at index {index}"
            )
        normalized = _validate_run(run, page, index)
        run_id = normalized["id"]
        if run_id in page_run_ids:
            raise RuntimeError(
                f"GitHub Actions API page {page} contained duplicate run id {run_id}"
            )
        page_run_ids.add(run_id)
        validated.append(normalized)
    return validated


def _response_media_type(response: object) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        raise RuntimeError("GitHub Actions API response did not include headers")
    get_content_type = getattr(headers, "get_content_type", None)
    if not callable(get_content_type):
        raise RuntimeError("GitHub Actions API response headers were not readable")
    media_type = str(get_content_type()).lower()
    if media_type not in EXPECTED_MEDIA_TYPES:
        raise RuntimeError(
            f"GitHub Actions API returned unexpected content type: {media_type}"
        )
    return media_type


def _response_content_length(response: object) -> int | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        raise RuntimeError("GitHub Actions API response did not include headers")
    get_header = getattr(headers, "get", None)
    if not callable(get_header):
        raise RuntimeError("GitHub Actions API response headers were not readable")
    raw_length = get_header("Content-Length")
    if raw_length in (None, ""):
        return None
    try:
        length = int(str(raw_length))
    except ValueError as exc:
        raise RuntimeError("GitHub Actions API returned an invalid Content-Length") from exc
    if length < 0:
        raise RuntimeError("GitHub Actions API returned an invalid Content-Length")
    if length > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            f"GitHub Actions API response exceeded the {MAX_RESPONSE_BYTES}-byte limit"
        )
    return length


def _read_json_payload(response: object) -> object:
    _response_media_type(response)
    declared_length = _response_content_length(response)
    read = getattr(response, "read", None)
    if not callable(read):
        raise RuntimeError("GitHub Actions API response body was not readable")
    body = read(MAX_RESPONSE_BYTES + 1)
    if not isinstance(body, bytes):
        raise RuntimeError("GitHub Actions API response body was not bytes")
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            f"GitHub Actions API response exceeded the {MAX_RESPONSE_BYTES}-byte limit"
        )
    if declared_length is not None and len(body) != declared_length:
        raise RuntimeError("GitHub Actions API response body length did not match Content-Length")
    try:
        return json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("GitHub Actions API returned malformed JSON") from exc


def _fetch_page(repository: str, sha: str, token: str, page: int) -> list[dict]:
    query = urlencode({"head_sha": sha, "per_page": PER_PAGE, "page": page})
    url = f"https://api.github.com/repos/{repository}/actions/runs?{query}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lionsforge-release-gate-verifier",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API host
            payload = _read_json_payload(response)
    except (HTTPError, URLError, SocketTimeout, TimeoutError, IncompleteRead) as exc:
        raise RuntimeError(f"GitHub Actions API request failed: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"GitHub Actions API response read failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub Actions API response was not an object")
    return _validate_page_runs(payload.get("workflow_runs"), page)


def fetch_runs(repository: str, sha: str, token: str) -> list[dict]:
    validate_inputs(repository, sha)
    runs: list[dict] = []
    seen_run_ids: set[int] = set()

    for page in range(1, MAX_PAGES + 1):
        page_runs = _fetch_page(repository, sha, token, page)
        page_ids = {run["id"] for run in page_runs}
        duplicate_ids = page_ids & seen_run_ids
        if duplicate_ids:
            duplicate_list = ", ".join(str(run_id) for run_id in sorted(duplicate_ids))
            raise RuntimeError(
                f"GitHub Actions API pagination repeated run id(s): {duplicate_list}"
            )
        seen_run_ids.update(page_ids)
        runs.extend(page_runs)
        if len(page_runs) < PER_PAGE:
            return runs

    raise RuntimeError(
        f"GitHub Actions API pagination exceeded the {MAX_PAGES}-page safety limit"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    try:
        validate_inputs(args.repository, args.sha)
        runs = fetch_runs(args.repository, args.sha, token)
        results = evaluate_runs(runs, expected_sha=args.sha)
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "repository": args.repository,
        "release_sha": args.sha,
        "required_event": REQUIRED_EVENT,
        "required_branch": REQUIRED_BRANCH,
        "required_workflow_paths": REQUIRED_WORKFLOW_PATHS,
        "passed": all_passed(results, expected_sha=args.sha),
        "gates": [result.__dict__ for result in results],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    print(rendered)
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
