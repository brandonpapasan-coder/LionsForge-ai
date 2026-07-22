# Internal Alpha Readiness Gate

Tracks #461. Related operational blockers: #29, #400, #401, #402, and #403.

This record governs LionsForge AI's transition from enterprise integration and operations into Internal Alpha. It is an operational control, not a claim of deployment, legal approval, security certification, or production readiness.

Do not store secrets, credentials, private user content, identity documents, private prompts, evidence payloads, or non-public personal information in this record. Evidence references may point to controlled systems.

## Decision

- Candidate commit SHA: `PENDING`
- Candidate backend image digest: `PENDING`
- Candidate frontend image digest: `PENDING`
- Candidate mobile build identifier: `NOT APPLICABLE OR PENDING`
- Review owner role: `PENDING`
- Review date: `PENDING`
- Decision: **NO-GO**

Any `PENDING`, `NOT VERIFIED`, `NOT TESTED`, unresolved high-severity defect, missing mandatory owner, or candidate-SHA mismatch keeps the decision at **NO-GO**.

Internal Alpha approval does not authorize public registration, public beta, general availability, live trading, brokerage, portfolio execution, or automated market orders.

## 1. Candidate integrity

| Control | Required evidence | Status |
|---|---|---|
| Candidate SHA exists on protected `main` | Commit and repository reference | NOT VERIFIED |
| Required CI checks passed on unchanged SHA | Backend CI, Frontend CI, Security Gate, Deployment Validation | NOT VERIFIED |
| Backend image is immutable | Registry digest mapped to candidate SHA | NOT VERIFIED |
| Frontend image is immutable | Registry digest mapped to candidate SHA | NOT VERIFIED |
| Mobile build provenance is traceable when applicable | Build identifier mapped to candidate SHA | NOT APPLICABLE OR NOT VERIFIED |
| Database migrations match candidate | Migration head and validation evidence | NOT VERIFIED |
| No unreviewed release override was used | Protected-environment audit reference | NOT VERIFIED |

## 2. Internal Alpha environment

| Dependency | Owner role | Evidence reference | Status |
|---|---|---|---|
| Kubernetes namespace or approved equivalent | PENDING | PENDING | NOT VERIFIED |
| PostgreSQL database and backups | PENDING | PENDING | NOT VERIFIED |
| API ingress, DNS, and HTTPS | PENDING | PENDING | NOT VERIFIED |
| Frontend ingress, DNS, and HTTPS | PENDING | PENDING | NOT VERIFIED |
| Secret and variable configuration | PENDING | PENDING | NOT VERIFIED |
| Container-registry access | PENDING | PENDING | NOT VERIFIED |
| OpenAI/provider configuration | PENDING | PENDING | NOT VERIFIED |
| Email, notification, or support integrations used by alpha | PENDING | PENDING | NOT APPLICABLE OR NOT VERIFIED |
| Mobile distribution channel used by alpha | PENDING | PENDING | NOT APPLICABLE OR NOT VERIFIED |

## 3. Integrated product journeys

Every mandatory journey must be tested using alpha-safe accounts and non-sensitive test data.

| Journey | Result | Evidence reference |
|---|---|---|
| Registration or controlled account provisioning | NOT TESTED | PENDING |
| Authentication, session renewal, and logout | NOT TESTED | PENDING |
| Research project and investigation creation | NOT TESTED | PENDING |
| Evidence ingestion and provenance display | NOT TESTED | PENDING |
| Claim validation and quality assessment | NOT TESTED | PENDING |
| Research conclusion and export workflows | NOT TESTED | PENDING |
| Knowledge graph and reusable research memory | NOT TESTED | PENDING |
| Personal memory controls and owner isolation | NOT TESTED | PENDING |
| Education Hub, assessments, mastery, and learning guidance | NOT TESTED | PENDING |
| Mentor or Copilot guidance and unavailable states | NOT TESTED | PENDING |
| Executive intelligence and governance views | NOT TESTED | PENDING |
| Enterprise administration and access controls | NOT TESTED | PENDING |
| Supported mobile journeys | NOT APPLICABLE OR NOT TESTED | PENDING |
| Account closure and data-removal workflow | NOT TESTED | PENDING |

## 4. Cross-system integration

| Integration control | Status | Evidence reference |
|---|---|---|
| API and frontend contracts match exported OpenAPI schema | NOT VERIFIED | PENDING |
| Authentication and authorization are consistent across surfaces | NOT VERIFIED | PENDING |
| Owner-scoped data cannot be read by another alpha user | NOT VERIFIED | PENDING |
| Research evidence references remain traceable across exports | NOT VERIFIED | PENDING |
| Knowledge-memory links preserve provenance and authorship labels | NOT VERIFIED | PENDING |
| Education recommendations distinguish measurements from guidance | NOT VERIFIED | PENDING |
| Provider timeouts fail safely without fabricated output | NOT VERIFIED | PENDING |
| Legacy finance modules remain disabled unless explicitly approved | NOT VERIFIED | PENDING |
| No live-trading or automated-execution route is enabled | NOT VERIFIED | PENDING |

## 5. Reliability and performance

- Availability observation window: `PENDING`
- API latency target and result: `PENDING`
- Frontend performance target and result: `PENDING`
- Database health and connection-pool result: `PENDING`
- Provider timeout and retry result: `PENDING`
- Error-rate target and result: `PENDING`
- Concurrent alpha-user target and result: `PENDING`
- Background-job or queue health when applicable: `PENDING`
- Mobile crash-free result when applicable: `PENDING`
- Open high or critical reliability defects: `PENDING`

## 6. Security and privacy

| Gate | Status | Evidence reference |
|---|---|---|
| Dependency audit | NOT VERIFIED | PENDING |
| Static security scan | NOT VERIFIED | PENDING |
| Authentication and authorization tests | NOT VERIFIED | PENDING |
| Secret scanning and credential review | NOT VERIFIED | PENDING |
| Log-redaction review | NOT VERIFIED | PENDING |
| Private prompt and evidence minimization review | NOT VERIFIED | PENDING |
| Data-retention behavior for alpha | NOT APPROVED | PENDING |
| Account deletion or de-identification test | NOT TESTED | PENDING |
| Security-report escalation path | NOT VERIFIED | PENDING |
| Open high or critical security/privacy defects | PENDING | PENDING |

## 7. Observability and operations

- API health dashboard: `PENDING`
- Frontend availability dashboard: `PENDING`
- Database health dashboard: `PENDING`
- Provider usage and cost dashboard: `PENDING`
- Error tracking and alert routing: `PENDING`
- Audit-log access owner: `PENDING`
- Alpha support owner and contact channel: `PENDING`
- Incident commander role: `PENDING`
- After-hours coverage position: `PENDING`
- Daily alpha review cadence: `PENDING`

## 8. Recovery and rollback

| Exercise | Result | Evidence reference |
|---|---|---|
| Backend rollback to prior immutable digest | NOT TESTED | PENDING |
| Frontend rollback to prior immutable digest | NOT TESTED | PENDING |
| Database migration rollback or approved forward-recovery procedure | NOT TESTED | PENDING |
| Backup restoration | NOT TESTED | PENDING |
| Provider outage behavior | NOT TESTED | PENDING |
| Credential rotation procedure | NOT TESTED | PENDING |
| Alpha access suspension | NOT TESTED | PENDING |

## 9. Alpha cohort controls

- Maximum approved alpha users: `PENDING`
- Enrollment method: `PENDING`
- Approved user roles: `PENDING`
- Quotas and rate limits: `PENDING`
- Allowed data classification: `PENDING`
- Prohibited data classes: `PENDING`
- Feedback and defect-intake channel: `PENDING`
- User acknowledgment or internal-use notice: `PENDING`
- Exit and account-cleanup procedure: `PENDING`

## 10. Open blockers

| Blocker | Severity | Owner role | Target resolution | Status |
|---|---|---|---|---|
| Staging or alpha environment provisioning | BLOCKING | PENDING | PENDING | OPEN |
| Candidate-SHA selection and validation | BLOCKING | PENDING | PENDING | OPEN |
| Integrated acceptance execution | BLOCKING | PENDING | PENDING | OPEN |
| Observability and incident routing | BLOCKING | PENDING | PENDING | OPEN |
| Security, privacy, and retention review | BLOCKING | PENDING | PENDING | OPEN |
| Rollback and restore exercises | BLOCKING | PENDING | PENDING | OPEN |

## 11. Final authorization

| Approval | Approver role | Date | Status |
|---|---|---|---|
| Product owner | PENDING | PENDING | NOT APPROVED |
| Engineering owner | PENDING | PENDING | NOT APPROVED |
| Security owner | PENDING | PENDING | NOT APPROVED |
| Privacy or data owner | PENDING | PENDING | NOT APPROVED |
| Operations owner | PENDING | PENDING | NOT APPROVED |
| Alpha support owner | PENDING | PENDING | NOT APPROVED |
| Release owner | PENDING | PENDING | NOT APPROVED |

## GO rule

Set the decision to **GO** only when all of the following are true:

1. One unchanged candidate SHA and its immutable artifacts are identified.
2. All required CI and security checks pass on that SHA.
3. The Internal Alpha environment is provisioned and verified.
4. Every mandatory integrated journey passes with traceable evidence.
5. Owner isolation, provenance, advisory-labeling, and disabled live-execution boundaries are verified.
6. Reliability, observability, cost, and provider-failure behavior meet approved alpha targets.
7. No unresolved high or critical security, privacy, reliability, or data-integrity defect remains.
8. Rollback, restore, incident response, and alpha-access suspension exercises pass.
9. Cohort size, quotas, data restrictions, support ownership, and feedback channels are approved.
10. Every required approver records approval for the exact candidate SHA.

Until then, the decision remains **NO-GO**.