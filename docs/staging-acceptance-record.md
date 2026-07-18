# LionsForge AI Staging Acceptance Record

Complete one copy of this record for each release candidate. Do not include secret values, access tokens, kubeconfig content, credentials, or sensitive user data.

## Release identity

- Release candidate SHA:
- Staging deploy workflow run:
- Staging frontend deploy workflow run:
- Staging URL:
- Acceptance date/time (UTC):
- Acceptance owner:
- Backend image digest:
- Running backend image digest verified: Yes / No
- Frontend image digest:
- Running frontend image digest verified: Yes / No
- Previous deployable image SHA:
- Database migration revision before deploy:
- Database migration revision after deploy:

## Automated validation

| Gate | Result | Run or evidence reference | Notes |
|---|---|---|---|
| Backend CI | Pending | | |
| Frontend CI | Pending | | |
| Security Gate | Pending | | |
| Deployment Validation | Pending | | |
| Staging Deploy | Pending | | |
| Staging Frontend Deploy | Pending | | |
| Authenticated smoke test | Pending | | |
| OpenAI provider health | Pending | | Record only enabled/status/model metadata. |
| Mentor schema validation | Pending | | Do not copy sensitive conversation data. |

Allowed results: `Passed`, `Failed`, `Blocked`, `Not run`.

## Infrastructure readiness

| Check | Result | Owner | Notes |
|---|---|---|---|
| Kubernetes cluster and namespace | Pending | | |
| Ingress, DNS, and HTTPS | Pending | | |
| PostgreSQL connectivity | Pending | | |
| Database backup and restore test | Pending | | |
| GHCR image-pull access | Pending | | |
| Error and latency observability | Pending | | |
| Acceptance user provisioned | Pending | | |

## Manual acceptance journey

| Step | Result | Evidence reference | Notes |
|---|---|---|---|
| Sign in and load Executive Dashboard | Pending | | |
| Create research project and save notebook | Pending | | |
| Create and reopen research session | Pending | | |
| Open Mentor with resolved research context | Pending | | |
| Receive complete evidence-first Mentor response | Pending | | |
| Reopen and continue Mentor conversation | Pending | | |
| Start and complete Education lesson | Pending | | |
| Verify market-learning panels and disclaimers | Pending | | |
| Sign out and sign back in | Pending | | |
| Verify persisted research, mentor, education, and learning state | Pending | | |
| Execute rollback verification | Pending | | |

## Defects

| Severity | Issue | Owner | Status | Release impact |
|---|---|---|---|---|
| | | | | |

Severity definitions:

- `Critical`: security isolation failure, credential exposure, unrecoverable data loss, or complete service outage.
- `High`: required user journey failure, unreliable persistence, provider failure without fallback, or unsafe rollback.
- `Medium`: degraded but recoverable workflow with a documented workaround.
- `Low`: cosmetic, copy, or non-blocking usability defect.

## Rollback evidence

- Previous image successfully identified: Yes / No
- Migration boundary reviewed: Yes / No
- Rollback command or workflow executed: Yes / No
- Service health restored after rollback: Yes / No
- Forward redeploy completed after rollback test: Yes / No
- Notes:

## Final decision

- Decision: `GO` / `NO-GO`
- Decision owner:
- Decision timestamp (UTC):
- Unresolved critical defects:
- Unresolved high-severity defects:
- Conditions or follow-up actions:

### Required sign-off statement

> I verified that this decision is based on the exact release candidate SHA and backend and frontend image digests recorded above, that the running staging backend and frontend images matched those digests, that no credentials are included in this record, and that all blocking gates and defects have been evaluated according to `docs/release-checklist.md`.
