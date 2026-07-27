# LionsForge AI staging acceptance record

The staging acceptance record is the deterministic evidence bundle for issue #29. It binds one protected-main candidate to the full staging acceptance evidence set and records either `GO` or `NO-GO`.

It does not provision infrastructure, deploy workloads, perform live checks, or authorize production, beta, legal, or general availability.

## Required evidence categories

Supply exactly one record for each category, sorted by category name:

- `backend_deployment`
- `backup_restore`
- `candidate_manifest`
- `frontend_deployment`
- `https_api_smoke`
- `https_web_smoke`
- `observability`
- `rollback`
- `staging_preflight`
- `staging_preflight_upload_receipt`

Each evidence item must contain only these fields:

```json
{
  "category": "backend_deployment",
  "candidate_sha": "0123456789abcdef0123456789abcdef01234567",
  "artifact_id": 123456,
  "artifact_url": "https://github.com/example/repository/actions/runs/1/artifacts/123456",
  "artifact_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "verified": true,
  "status": "passed",
  "observed_at": "2026-07-27T21:30:00Z",
  "summary": "Backend image digest and running-container digest were verified for the candidate."
}
```

Allowed status values are `passed`, `failed`, and `incomplete`.

## Decision behavior

`GO` is produced only when every required item:

- is structurally valid;
- is marked `verified: true`;
- has `status: passed`;
- uses the exact candidate SHA;
- includes a positive artifact ID, HTTPS artifact URL, SHA-256 artifact digest, UTC observation time, and bounded summary.

Structurally valid evidence that is failed, incomplete, unverified, or candidate-mismatched produces a valid receipted `NO-GO` record. Missing, duplicate, extra, malformed, sensitive, or tampered evidence is rejected.

## Local generation

Create an input file with the candidate identity, rationale, UTC generation time, and all ten evidence records:

```json
{
  "candidate_sha": "0123456789abcdef0123456789abcdef01234567",
  "selection_rationale": "Fresh protected-main candidate selected for staging acceptance.",
  "generated_at": "2026-07-27T21:30:00Z",
  "evidence": []
}
```

Run:

```bash
python scripts/manage_staging_acceptance_record.py generate \
  staging-acceptance-input.json \
  --output staging-acceptance-record.json

python scripts/manage_staging_acceptance_record.py validate \
  staging-acceptance-record.json
```

Exit codes:

- `0`: valid `GO` bundle or successful validation;
- `2`: valid generated `NO-GO` bundle;
- `1` or another nonzero code: malformed input or invalid bundle.

## GitHub workflow

Dispatch **Staging Acceptance Record** with:

- the exact protected-main candidate SHA;
- the candidate-selection rationale;
- the JSON array containing all ten evidence records.

The workflow verifies candidate identity and ancestry, generates and validates the bundle, uploads `staging-acceptance-record-<candidate_sha>` with 90-day retention, and publishes the artifact ID, URL, digest, and decision.

A valid `NO-GO` bundle is uploaded before the workflow fails so the blocking evidence remains auditable.

## Operator acceptance checklist

Before supplying evidence, independently verify:

- the candidate manifest and staging-preflight receipt are valid and candidate-bound;
- backend and frontend registry digests match running containers;
- API and web HTTPS smoke checks passed;
- rollback was executed successfully;
- backup and restore were exercised successfully;
- observability evidence demonstrates usable health, error, and latency visibility.

Do not mark an item passed merely because an artifact exists. `verified: true` means an operator independently checked the artifact contents and candidate binding.

## Handling rules

Never include secrets, tokens, passwords, API keys, private user data, request content, kubeconfig values, database URLs, credentials, or raw customer material. Store only evidence identifiers, digests, bounded summaries, verification results, and timestamps.

The record is repository evidence only. Independent operators must still provision staging and execute every live acceptance exercise required by issue #29.
