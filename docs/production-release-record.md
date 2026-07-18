# LionsForge AI Production Release Record

Complete one copy of this record for every production deployment. Do not include secret values, credentials, private evidence, or session data.

## Release identity

- Release owner:
- Deployment executor:
- Release commit SHA:
- Rollback commit SHA:
- Production workflow run:
- Deployment date (UTC):
- Final decision: GO / NO-GO

## Required exact-head gates

Record the run identifier and conclusion for the release SHA.

- Backend CI:
- Frontend CI:
- Security Gate:
- Deployment Validation:

All four conclusions must be successful before production approval.

## Environment readiness

- GitHub `production` environment requires manual approval: PASS / FAIL
- `PRODUCTION_API_URL` is a valid HTTPS endpoint: PASS / FAIL
- `KUBE_CONFIG_PRODUCTION` is configured: PASS / FAIL
- `PRODUCTION_DATABASE_URL` is configured: PASS / FAIL
- `PRODUCTION_JWT_SECRET_KEY` is configured and non-default: PASS / FAIL
- `PRODUCTION_OPENAI_API_KEY` is configured: PASS / FAIL
- `PRODUCTION_TEST_EMAIL` is configured: PASS / FAIL
- `PRODUCTION_TEST_SECRET` is configured: PASS / FAIL
- Production namespace, ingress, DNS, TLS, database, and GHCR pull access are operational: PASS / FAIL

Never paste the values of these settings into this record.

## Deployment validation

- Exact release commit was checked out: PASS / FAIL
- Release commit is contained in `main`: PASS / FAIL
- Immutable backend image built and pushed: PASS / FAIL
- Production manifests applied successfully: PASS / FAIL
- Backend rollout completed: PASS / FAIL
- Deployed image matches the release SHA: PASS / FAIL
- Backend readiness and liveness probes are healthy: PASS / FAIL

## Smoke validation

- Health endpoint: PASS / FAIL
- Readiness endpoint: PASS / FAIL
- Authentication: PASS / FAIL
- Dashboard API: PASS / FAIL
- Research project workflow: PASS / FAIL
- Research session workflow: PASS / FAIL
- Mentor workflow: PASS / FAIL
- Education and assessment workflow: PASS / FAIL
- Evidence-validation workflow: PASS / FAIL
- Knowledge-quality workflow: PASS / FAIL
- Stable user-facing error handling: PASS / FAIL
- No internal service details exposed: PASS / FAIL

## Scope and safety validation

- Release remains within the research-assistant, evidence-validation, knowledge-management, and education scope: PASS / FAIL
- No live trading, brokerage, order routing, autonomous portfolio management, individualized financial advice, or personalized securities recommendations were introduced: PASS / FAIL
- Legacy finance and market-learning surfaces are absent from the default production experience: PASS / FAIL
- If compatibility mode is intentionally enabled, its scope, owner, migration purpose, access controls, and educational disclaimers are documented: PASS / FAIL / NOT ENABLED

## Rollback readiness

- Rollback image exists and is pullable: PASS / FAIL
- Rollback SHA identifies the previously deployed release: PASS / FAIL
- Database migration boundary reviewed: PASS / FAIL
- Backup or restore checkpoint confirmed where required: PASS / FAIL
- Rollback executor identified: PASS / FAIL

## Observability and ownership

- Backend and frontend health monitoring active: PASS / FAIL
- Error and latency alerts routed: PASS / FAIL
- Security and incident-response owner identified: PASS / FAIL
- Post-release validation owner identified: PASS / FAIL

## Known limitations

- None recorded / list limitations:

## Decision

A **GO** decision requires every mandatory item above to pass and no unresolved critical or high-severity defect. Record the reason for any **NO-GO** decision.

- Decision rationale:
- Approver:
- Approval timestamp (UTC):
