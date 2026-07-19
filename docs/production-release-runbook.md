# Production Release Runbook

This runbook supports Issue #401 and the launch-control epic #400. Never store credentials, tokens, kubeconfig content, secret values, or private user data in source control, issue comments, workflow output, or acceptance records.

## 1. Entry criteria

Production work may begin only after:

- Issue #29 has a recorded staging `GO` decision.
- One exact release SHA from `main` passed Backend CI, Frontend CI, Security Gate, and Deployment Validation.
- Backend and frontend staging deployments used that exact SHA and immutable image digests.
- Staging rollback, backup/restore, observability, and required user journeys passed.
- A distinct previously deployed rollback SHA is available.
- A named release owner and approver are recorded.

## 2. Protected GitHub environment

Create or verify the `production` environment with required reviewers and deployment protection rules.

Required non-secret variables:

- `PRODUCTION_API_URL`
- `PRODUCTION_WEB_URL`

Required secrets:

- `KUBE_CONFIG_PRODUCTION`
- `PRODUCTION_DATABASE_URL`
- `PRODUCTION_JWT_SECRET_KEY`
- `PRODUCTION_OPENAI_API_KEY`
- `PRODUCTION_TEST_EMAIL`
- `PRODUCTION_TEST_SECRET`

The API and web URLs must be non-empty HTTPS origins. Production and staging credentials must be different.

## 3. Infrastructure readiness

Verify:

- `lionsforge-production` Kubernetes namespace or dedicated cluster
- production PostgreSQL connectivity, encryption, backups, deletion protection, and restore access
- ingress, DNS, and valid TLS for API and web endpoints
- GHCR image-pull access
- resource requests and limits
- autoscaling or documented capacity limits
- pod disruption and availability settings
- centralized logs, latency/error metrics, uptime checks, and alerts
- OpenAI usage limits, timeout behavior, budget alerts, and cost dashboards
- production admin and acceptance accounts

## 4. Run preflight

From a trusted operator workstation:

```bash
export RELEASE_SHA=<40-character-main-sha>
export ROLLBACK_SHA=<40-character-previous-release-sha>
export PRODUCTION_API_URL=https://api.lionsforge.ai
export PRODUCTION_WEB_URL=https://app.lionsforge.ai
bash scripts/production-preflight.sh
```

A passing preflight is necessary but does not authorize deployment by itself.

## 5. Deploy backend

Dispatch `Production Deploy` with the approved release and rollback SHAs.

Record:

- workflow run ID
- release and rollback SHAs
- backend registry digest
- running backend image digest verification
- migration revision before and after deployment
- authenticated smoke-test result

Do not proceed to frontend deployment if backend rollout, probes, migrations, or authenticated smoke testing fail.

## 6. Deploy frontend

Dispatch `Production Frontend Deploy` using the same release and rollback SHAs.

Record:

- workflow run ID
- frontend registry digest
- running frontend image digest verification
- HTTPS login-page smoke result

Backend and frontend must use the same approved source SHA.

## 7. Live acceptance

Validate at minimum:

- registration or controlled invitation path
- sign in, sign out, and session persistence
- dashboard availability
- investigation creation, claims, evidence, validation, and education recommendations
- Mentor healthy behavior and deterministic unavailable/fallback handling
- Education lesson and adaptive assessment authority
- owner isolation and answer-key privacy
- account/support/deletion workflows when enabled
- logging, alerts, latency, error rates, database health, and OpenAI spend

## 8. Rollback and restore

Before public access expands:

- review the database migration boundary
- execute the approved rollback procedure using the recorded rollback SHA
- verify service health after rollback
- forward-deploy the approved release again
- execute or verify a production-safe backup restore exercise
- record evidence without secrets or private data

## 9. GO or NO-GO

A named owner records `GO` only when:

- exact release SHA and both image digests are verified
- backend and frontend workflows pass
- critical user journeys pass
- rollback and restore are verified
- alerts and observability are active
- no unresolved critical or high-severity defects remain
- legal, privacy, support, retention, deletion, and beta access controls are ready

Otherwise record `NO-GO` with blockers, owners, and remediation actions.
