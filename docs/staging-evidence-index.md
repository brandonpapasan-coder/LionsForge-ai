# Staging Evidence Index

The Staging Evidence Index binds the retained repository and staging artifacts for one protected-main candidate into a deterministic, receipted package.

It is evidence-index tooling only. It does not provision infrastructure, deploy workloads, execute live checks, or authorize staging, production, beta, legal, or general-availability readiness.

## Required entries

Supply exactly one entry for each category, in any input order. The generator sorts them canonically:

- `backend_deployment`
- `candidate_manifest`
- `candidate_manifest_artifact`
- `frontend_deployment`
- `staging_acceptance_record`
- `staging_preflight_evidence`
- `staging_preflight_upload_receipt`

Each entry must contain only:

- `category`
- `candidate_sha`
- `artifact_id`
- `artifact_url`
- `artifact_digest`
- `workflow_run_id`
- `verified`
- `status`
- `decision`
- `observed_at`
- `summary`

Do not include credentials, tokens, secret names or values, private user data, request content, or sensitive evidence payloads.

## Entry contract

- `candidate_sha`: exact lowercase 40-character SHA matching the index candidate.
- `artifact_id` and `workflow_run_id`: positive integers.
- `artifact_url`: HTTPS artifact or workflow evidence URL.
- `artifact_digest`: lowercase `sha256:` digest.
- `verified`: boolean indicating the operator independently verified the reference and binding.
- `status`: `passed`, `failed`, or `incomplete`.
- `decision`: `GO`, `NO-GO`, or `NOT-APPLICABLE`.
- `observed_at`: UTC timestamp ending in `Z`.
- `summary`: non-sensitive explanation, 1–500 characters.

The `staging_acceptance_record` entry must be verified, passed, candidate-bound, and `GO` for the index to become `READY`. Any failed, incomplete, unverified, mismatched, or `NO-GO` mandatory entry produces a valid auditable `NOT-READY` index.

## Local generation

Create a JSON input with `candidate_sha`, `selection_rationale`, `generated_at`, and `entries`, then run:

```bash
python scripts/manage_staging_evidence_index.py generate \
  staging-evidence-index-input.json \
  --output staging-evidence-index.json
```

Exit codes:

- `0`: valid `READY` index generated.
- `2`: valid `NOT-READY` index generated.
- other nonzero: malformed input or execution failure.

Validate an existing bundle with:

```bash
python scripts/manage_staging_evidence_index.py validate staging-evidence-index.json
```

## GitHub workflow

Dispatch **Staging Evidence Index** with:

- a fresh exact candidate SHA contained in protected `main`;
- a bounded selection rationale;
- the complete evidence-entry JSON array.

The workflow checks out the exact candidate, verifies `origin/main` ancestry, generates and validates the bundle, uploads it for 90 days, publishes artifact identity and digest, and then fails closed unless the index records `READY`.

A `NOT-READY` bundle is intentionally uploaded before enforcement so the blocking state remains available for audit. It must not be treated as launch approval.
