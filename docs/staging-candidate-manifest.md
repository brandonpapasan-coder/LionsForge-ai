# Staging candidate manifest

The staging candidate manifest is a deterministic repository-evidence bundle used before staging preflight. It binds one fresh protected-`main` commit to the five authoritative workflow runs required by issue #29.

It does **not** authorize staging, production, controlled beta, public registration, or general availability.

## Required evidence

Provide one exact lowercase 40-character candidate SHA and successful workflow run IDs for:

1. Backend CI
2. Deployment Validation
3. Frontend CI
4. Internal Alpha Upload Receipt CI
5. Security Gate

The `Staging Preflight` workflow retrieves these runs directly through the GitHub Actions API. Operators do not enter workflow names, conclusions, run numbers, or head SHAs. The manifest validator obtains and verifies those values from GitHub.

The workflow also requires a concise candidate-selection rationale. Never include secrets, tokens, API keys, private user content, request contents, or private acceptance evidence in the rationale.

## Workflow execution

Dispatch `.github/workflows/staging-preflight.yml` with:

- `candidate_sha`
- `selection_rationale`
- `backend_ci_run_id`
- `deployment_validation_run_id`
- `frontend_ci_run_id`
- `internal_alpha_receipt_run_id`
- `security_gate_run_id`
- `skip_endpoints`, only when intentionally performing configuration-only validation

The workflow:

1. validates the candidate input;
2. checks out the exact candidate;
3. verifies the candidate is contained in `origin/main`;
4. retrieves all five authoritative workflow runs through `gh api` using read-only Actions permission;
5. writes the strict generation input;
6. generates and validates the manifest bundle;
7. requires the manifest decision to be `GO` before AWS or endpoint checks;
8. uploads `staging-candidate-manifest-<sha>` with 90-day retention;
9. publishes the manifest artifact ID, URL, and upload digest in the workflow summary;
10. continues with the existing staging configuration, endpoint, provenance, and upload-receipt controls.

Any missing, duplicate, unknown, unsuccessful, incomplete, or candidate-mismatched workflow run causes failure before staging validation proceeds.

## Local generation

Create an input document containing only:

```json
{
  "candidate_sha": "0123456789abcdef0123456789abcdef01234567",
  "selection_rationale": "Fresh protected-main candidate selected after the latest launch-critical merge.",
  "protected_main_ancestry_verified": true,
  "generated_at": "2026-07-27T20:00:00Z",
  "workflow_runs": []
}
```

Generate a bundle:

```bash
python scripts/manage_staging_candidate_manifest.py generate input.json manifest.json
```

Validate a bundle:

```bash
python scripts/manage_staging_candidate_manifest.py validate manifest.json
```

Exit codes:

- `0`: structurally valid bundle with a `GO` decision
- `2`: structurally valid bundle with a `NO-GO` decision
- other nonzero: malformed input or invalid bundle

## Retained evidence

Retain the manifest artifact together with:

- the staging-preflight report artifact;
- the deterministic staging-preflight upload receipt;
- backend and frontend registry digests;
- running-container digest verification;
- smoke, migration, rollback, backup/restore, observability, and acceptance evidence.

A `GO` manifest means only that repository candidate evidence is internally consistent. Live staging acceptance remains **NO-GO** until every external requirement in issue #29 is independently executed and verified.
