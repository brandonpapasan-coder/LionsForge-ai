# Staging candidate manifest

The staging candidate manifest is a repository-evidence record used before live staging preflight. It binds one exact protected-`main` commit to the five authoritative workflow runs required by issue #29.

It does **not** prove that staging infrastructure, HTTPS endpoints, deployment, rollback, backup/restore, observability, production, legal review, controlled beta, or general availability has completed.

## Required workflow evidence

The generation input must contain exactly these workflows:

1. Backend CI
2. Deployment Validation
3. Frontend CI
4. Internal Alpha Upload Receipt CI
5. Security Gate

Each workflow record must include:

- `name`
- positive integer `run_id`
- positive integer `run_number`
- `status` equal to `completed`
- `conclusion` equal to `success`
- `head_sha` equal to the selected candidate SHA

## Generate

Create a private local input file containing only non-sensitive workflow metadata:

```json
{
  "candidate_sha": "0123456789abcdef0123456789abcdef01234567",
  "selection_rationale": "Fresh protected-main candidate selected for staging acceptance after the latest launch-critical merge.",
  "protected_main_ancestry_verified": true,
  "generated_at": "2026-07-27T20:00:00Z",
  "workflow_runs": []
}
```

Then run:

```bash
python scripts/manage_staging_candidate_manifest.py generate \
  staging-candidate-input.json \
  --output staging-candidate-manifest.json
```

Exit codes:

- `0`: valid manifest with `GO`
- `2`: valid manifest with `NO-GO`
- other nonzero code: malformed or invalid input

## Validate

```bash
python scripts/manage_staging_candidate_manifest.py validate staging-candidate-manifest.json
```

Validation fails closed for missing, duplicate, extra, unsuccessful, stale, reordered, or mismatched workflow records; invalid ancestry evidence; candidate substitution; decision drift; receipt substitution; unexpected fields; and sensitive-field names.

## Operator rules

- Select a fresh candidate at execution time. Do not copy an old SHA from an issue, pull request, or prior acceptance record.
- Verify the candidate is contained in protected `origin/main` before setting `protected_main_ancestry_verified` to `true`.
- Use workflow runs tied to the exact candidate or its unchanged validated pull-request head before merge.
- Never include secrets, tokens, passwords, API keys, request contents, private user data, or private evidence.
- Retain the generated bundle with staging-preflight evidence.
- A manifest `GO` authorizes only continued staging verification. It is not public-launch approval.
