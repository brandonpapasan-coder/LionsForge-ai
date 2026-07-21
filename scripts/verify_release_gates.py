#!/usr/bin/env python3
"""Verify required GitHub Actions workflows succeeded for an exact commit SHA."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
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
            if run.get("name") == workflow_name
            and is_eligible_run(
                run,
                expected_sha=expected_sha,
                expected_path=workflow_path,
            )
        ]
        matches.sort(
            key=lambda run: (
                int(run.get("run_number") or 0),
                int(run.get("run_attempt") or 0),
                int(run.get("id") or 0),
            ),
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
                run.get("path"),
                str(run.get("status") or "unknown"),
                run.get("conclusion"),
                run.get("id"),
                run.get("html_url"),
                run.get("event"),
                run.get("head_branch"),
                run.get("head_sha"),
            )
        )
    return results


def all_passed(
    results: list[GateResult], expected_sha: str | None = None
) -> bool:
    return all(
        result.status == "completed"
        and result.conclusion == "success"
        and result.event == REQUIRED_EVENT
        and result.head_branch == REQUIRED_BRANCH
        and result.path == REQUIRED_WORKFLOW_PATHS[result.name]
        and (expected_sha is None or result.head_sha == expected_sha)
        for result in results
    )


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
            payload = json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GitHub Actions API request failed: {exc}") from exc
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise RuntimeError("GitHub Actions API response did not contain workflow_runs")
    return runs


def fetch_runs(repository: str, sha: str, token: str) -> list[dict]:
    validate_inputs(repository, sha)
    runs: list[dict] = []
    page = 1
    while True:
        page_runs = _fetch_page(repository, sha, token, page)
        runs.extend(page_runs)
        if len(page_runs) < PER_PAGE:
            return runs
        page += 1


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
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    results = evaluate_runs(runs, expected_sha=args.sha)
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
