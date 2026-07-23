# Internal Alpha Readiness Gate

Tracks #461. Primary operational blocker: #29. Related launch-control work: #400, #401, #402, and #403.

This record governs LionsForge AI's transition into Internal Alpha. It is a fail-closed operational control, not a claim of deployment, legal approval, security certification, production readiness, public beta, or general availability.

Do not store secrets, credentials, private user content, private prompts, evidence payloads, identity documents, or non-public personal information in this file.

## Current decision

- Protected-main implementation merge: `cd539d1eef52f1c46770a0f01b74ad0325ba5dca`
- Staging execution controls merge: `12002fcc4417163eee4bc4f3ae63d225a1db0b74`
- Pre-merge gate-clean candidate: `6cfc9e070f3b63717b4b6fa72250ea53abce9d9b`
- Backend image digest: `PENDING`
- Frontend image digest: `PENDING`
- Review owner role: `PENDING`
- Review date: `PENDING`
- Decision: **NO-GO**

Any `PENDING`, `NOT VERIFIED`, `NOT TESTED`, unresolved high or critical defect, missing mandatory owner, or candidate mismatch keeps the decision at **NO-GO**.

Internal Alpha approval does not authorize public registration, public beta, general availability, live trading, brokerage, custody, portfolio execution, or automated market orders.

## 1. Candidate integrity

| Control | Status | Evidence |
|---|---|---|
| Candidate implementation exists on protected `main` | VERIFIED | PR #465 / merge `cd539d1e...` |
| Backend CI passed on unchanged pre-merge candidate | VERIFIED | Run 1714 |
| Frontend CI passed on unchanged pre-merge candidate | VERIFIED | Run 1249 |
| Security Gate passed on unchanged pre-merge candidate | VERIFIED | Run 922 |
| Deployment Validation passed on unchanged pre-merge candidate | VERIFIED | Run 1504 |
| Candidate-specific staging execution record is versioned | VERIFIED | PR #468 / merge `12002fcc...` |
| Backend image is immutable and mapped to candidate | NOT VERIFIED | PENDING |
| Frontend image is immutable and mapped to candidate | NOT VERIFIED | PENDING |
| Running containers match recorded digests | NOT VERIFIED | PENDING |
| Database migration head matches deployed backend | NOT VERIFIED | PENDING |
| No release override bypassed protected controls | NOT VERIFIED | PENDING |

## 2. Internal Alpha environment

| Dependency | Status | Evidence |
|---|---|---|
| AWS cost approval and accountable owner | NOT APPROVED | PENDING |
| Terraform remote state and OIDC roles | NOT VERIFIED | PENDING |
| Reviewed Terraform plan | NOT EXECUTED | PENDING |
| Protected Terraform apply | NOT EXECUTED | PENDING |
| EKS cluster and `lionsforge-staging` namespace | NOT PROVISIONED | PENDING |
| PostgreSQL database, encryption, backups, and restore path | NOT PROVISIONED | PENDING |
| API ingress, DNS, and HTTPS | NOT PROVISIONED | PENDING |
| Frontend ingress, DNS, and HTTPS | NOT PROVISIONED | PENDING |
| GitHub `staging` environment variables and secrets | NOT CONFIGURED | PENDING |
| GitHub `staging-apply` protection and reviewers | NOT CONFIGURED | PENDING |
| GHCR pull access and immutable deployment | NOT VERIFIED | PENDING |
| OpenAI/provider configuration | NOT CONFIGURED | PENDING |
| Pre-provisioned alpha acceptance user | NOT CONFIGURED | PENDING |

## 3. Integrated product journeys

Every journey must use alpha-safe accounts and non-sensitive test data.

| Journey | Result | Evidence |
|---|---|---|
| Controlled account provisioning | NOT TESTED | PENDING |
| Authentication, session renewal, and logout | NOT TESTED | PENDING |
| Research project and investigation creation | NOT TESTED | PENDING |
| Evidence ingestion and provenance display | NOT TESTED | PENDING |
| Claim validation and quality assessment | NOT TESTED | PENDING |
| Research conclusion and export | NOT TESTED | PENDING |
| Knowledge graph and reusable research memory | NOT TESTED | PENDING |
| Personal memory controls and owner isolation | NOT TESTED | PENDING |
| Education Hub, assessments, mastery, and guidance | NOT TESTED | PENDING |
| Mentor/Copilot guidance and safe unavailable states | NOT TESTED | PENDING |
| Executive intelligence and governance views | NOT TESTED | PENDING |
| Enterprise administration and access controls | NOT TESTED | PENDING |
| Account closure and data removal | NOT TESTED | PENDING |

## 4. Cross-system controls

| Control | Status | Evidence |
|---|---|---|
| Frontend contracts match exported OpenAPI schema | NOT VERIFIED IN STAGING | PENDING |
| Authentication and authorization are consistent across surfaces | NOT VERIFIED IN STAGING | PENDING |
| Owner-scoped data cannot be read by another alpha user | NOT VERIFIED | PENDING |
| Evidence references remain traceable across exports | NOT VERIFIED | PENDING |
| Knowledge-memory links preserve provenance and authorship labels | NOT VERIFIED | PENDING |
| Education recommendations distinguish measurements from guidance | NOT VERIFIED | PENDING |
| Provider timeouts fail safely without fabricated output | NOT VERIFIED | PENDING |
| Legacy finance modules remain disabled | NOT VERIFIED IN STAGING | PENDING |
| No live-trading or automated-execution route is enabled | NOT VERIFIED IN STAGING | PENDING |

## 5. Reliability, security, and operations

- Availability observation window: `PENDING`
- API latency and error-rate targets/results: `PENDING`
- Frontend performance result: `PENDING`
- Database health and connection-pool result: `PENDING`
- Provider timeout/retry result: `PENDING`
- Concurrent alpha-user target/result: `PENDING`
- Dependency, static, secret, and container security evidence for deployed artifacts: `PENDING`
- Log-redaction and data-minimization review: `PENDING`
- Data-retention position and deletion test: `PENDING`
- API, frontend, database, provider-cost, and error dashboards: `PENDING`
- Alert routing, incident commander, support owner, and review cadence: `PENDING`

## 6. Recovery and rollback

| Exercise | Result | Evidence |
|---|---|---|
| Backend rollback to prior immutable digest | NOT TESTED | PENDING |
| Frontend rollback to prior immutable digest | NOT TESTED | PENDING |
| Database rollback or approved forward recovery | NOT TESTED | PENDING |
| Backup restoration | NOT TESTED | PENDING |
| Provider outage behavior | NOT TESTED | PENDING |
| Credential rotation | NOT TESTED | PENDING |
| Alpha access suspension | NOT TESTED | PENDING |

## 7. Alpha cohort controls

- Maximum approved alpha users: `PENDING`
- Enrollment method and approved roles: `PENDING`
- Quotas and rate limits: `PENDING`
- Allowed and prohibited data classes: `PENDING`
- Feedback and defect-intake channel: `PENDING`
- Internal-use acknowledgment: `PENDING`
- Exit and account-cleanup procedure: `PENDING`

## 8. Final authorization

| Approval | Status |
|---|---|
| Product owner | NOT APPROVED |
| Engineering owner | NOT APPROVED |
| Security owner | NOT APPROVED |
| Privacy/data owner | NOT APPROVED |
| Operations owner | NOT APPROVED |
| Alpha support owner | NOT APPROVED |
| Release owner | NOT APPROVED |

## GO rule

Set the decision to **GO** only when:

1. Immutable backend and frontend digests are mapped to one approved protected-main candidate.
2. Required CI, security, and deployment validation evidence is complete for that candidate and its deployed artifacts.
3. The Internal Alpha environment is provisioned, secured, observable, and verified.
4. Every mandatory integrated journey passes with traceable evidence.
5. Owner isolation, provenance, advisory labeling, and disabled live-execution boundaries are verified.
6. Reliability, performance, cost, and provider-failure behavior meet approved targets.
7. No unresolved high or critical security, privacy, reliability, or data-integrity defect remains.
8. Rollback, restore, incident response, credential rotation, and access-suspension exercises pass.
9. Cohort size, quotas, data restrictions, support ownership, and feedback channels are approved.
10. Every required approver records approval for the exact candidate and deployed digests.

Until then, the decision remains **NO-GO**.
