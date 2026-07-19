# LionsForge AI Production Acceptance Record

Complete one copy for each production release candidate. Do not include credentials, access tokens, kubeconfig content, secret values, private prompts, or sensitive user data.

## Release identity

- Release SHA:
- Rollback SHA:
- Staging GO evidence:
- Backend deploy workflow run:
- Frontend deploy workflow run:
- Production API URL:
- Production web URL:
- Release owner:
- Approval owner:
- Release date/time (UTC):
- Backend image digest:
- Running backend digest verified: Yes / No
- Frontend image digest:
- Running frontend digest verified: Yes / No
- Migration revision before deploy:
- Migration revision after deploy:

## Required gates

| Gate | Result | Evidence reference | Notes |
|---|---|---|---|
| Staging GO | Pending | | |
| Backend CI | Pending | | |
| Frontend CI | Pending | | |
| Security Gate | Pending | | |
| Deployment Validation | Pending | | |
| Production preflight | Pending | | |
| Backend production deploy | Pending | | |
| Frontend production deploy | Pending | | |
| Authenticated API smoke | Pending | | |
| Frontend HTTPS smoke | Pending | | |

Allowed results: `Passed`, `Failed`, `Blocked`, `Not run`.

## Infrastructure and operations

| Check | Result | Owner | Notes |
|---|---|---|---|
| Kubernetes production environment | Pending | | |
| PostgreSQL connectivity and encryption | Pending | | |
| DNS and valid HTTPS | Pending | | |
| Registry image-pull access | Pending | | |
| Resource requests and limits | Pending | | |
| Capacity or autoscaling controls | Pending | | |
| Backup retention | Pending | | |
| Restore exercise | Pending | | |
| Centralized logs | Pending | | |
| Availability, error, latency, and database alerts | Pending | | |
| OpenAI usage and budget alerts | Pending | | |
| Production admin and acceptance accounts | Pending | | |
| Least-privilege access review | Pending | | |

## Critical user journeys

| Journey | Result | Evidence reference | Notes |
|---|---|---|---|
| Controlled registration or invitation | Pending | | |
| Sign in and sign out | Pending | | |
| Session and persisted-state recovery | Pending | | |
| Dashboard | Pending | | |
| Create private investigation | Pending | | |
| Add claims and evidence | Pending | | |
| Record validation judgment | Pending | | |
| View education-gap recommendations | Pending | | |
| Mentor healthy response | Pending | | |
| Mentor unavailable/fallback behavior | Pending | | |
| Education lesson and adaptive assessment | Pending | | |
| Owner isolation | Pending | | |
| Answer-key privacy | Pending | | |
| Support request path | Pending | | |
| Account deletion and retention workflow | Pending | | |

## Rollback evidence

- Previous backend and frontend images identified: Yes / No
- Migration boundary reviewed: Yes / No
- Backend rollback executed: Yes / No
- Frontend rollback executed: Yes / No
- Service health restored: Yes / No
- Forward redeploy completed: Yes / No
- Notes:

## Defects

| Severity | Issue | Owner | Status | Release impact |
|---|---|---|---|---|
| | | | | |

Blocking severity definitions:

- `Critical`: security isolation failure, credential exposure, unrecoverable data loss, or complete service outage.
- `High`: required user journey failure, unreliable persistence, provider failure without safe fallback, unsafe rollback, or missing public privacy/support control.

## Final decision

- Decision: `GO` / `NO-GO`
- Decision owner:
- Decision timestamp (UTC):
- Unresolved critical defects:
- Unresolved high-severity defects:
- Conditions or follow-up actions:

### Required sign-off statement

> I verified that this decision is based on the exact release and rollback SHAs and backend and frontend image digests recorded above; that running production containers matched the recorded digests; that required staging, security, operational, privacy, support, rollback, restore, observability, and user-journey gates were evaluated; and that this record contains no credentials or sensitive user data.
