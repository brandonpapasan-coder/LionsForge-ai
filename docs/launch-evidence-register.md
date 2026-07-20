# LionsForge AI Launch Evidence Register

Parent epic: #400

Use this register to identify where launch evidence is stored. Store restricted operational material and private tester data only in approved systems. Repository records should contain references, timestamps, outcomes, and redacted evidence—not sensitive access details or personal research content.

## Evidence rules

- Every artifact must identify the exact release SHA and environment.
- Screenshots or logs must redact private access data, email addresses, prompts, and investigation content.
- A passing repository workflow is not proof that a live environment passed acceptance.
- A failed or incomplete artifact cannot be marked accepted.
- Superseded evidence must remain traceable to its replacement.

## Release provenance

| Evidence | Reference | SHA / digest | Date | Owner | Result |
|---|---|---|---|---|---|
| Selected `main` SHA |  |  |  |  |  |
| Backend CI |  |  |  |  |  |
| Frontend CI |  |  |  |  |  |
| Security Gate |  |  |  |  |  |
| Deployment Validation |  |  |  |  |  |
| Backend image digest |  |  |  |  |  |
| Frontend image digest |  |  |  |  |  |

## Staging acceptance

| Evidence | Reference | Date | Owner | Result | Notes |
|---|---|---|---|---|---|
| HTTPS API smoke |  |  |  |  |  |
| HTTPS web smoke |  |  |  |  |  |
| Migration |  |  |  |  |  |
| Authentication journey |  |  |  |  |  |
| Investigation and evidence journey |  |  |  |  |  |
| Validation and provenance journey |  |  |  |  |  |
| Education and Mentor journey |  |  |  |  |  |
| Provider timeout/unavailable behavior |  |  |  |  |  |
| Backup |  |  |  |  |  |
| Isolated restore |  |  |  |  |  |
| Rollback |  |  |  |  |  |

## Production and beta controls

| Evidence | Reference | Date | Owner | Result | Notes |
|---|---|---|---|---|---|
| Least-privilege access review |  |  |  |  |  |
| Registration cap |  |  |  |  |  |
| Per-user quota |  |  |  |  |  |
| Aggregate AI budget |  |  |  |  |  |
| Abuse control |  |  |  |  |  |
| Maintenance mode / emergency stop |  |  |  |  |  |
| API outage alert |  |  |  |  |  |
| Frontend outage alert |  |  |  |  |  |
| Database failure alert |  |  |  |  |  |
| Elevated error-rate alert |  |  |  |  |  |
| Budget threshold alert |  |  |  |  |  |
| Production backup |  |  |  |  |  |
| Production isolated restore |  |  |  |  |  |
| Production rollback |  |  |  |  |  |

## Policy and support

| Evidence | Reference | Effective date | Approver | Result |
|---|---|---|---|---|
| Privacy policy live |  |  |  |  |
| Terms live |  |  |  |  |
| Responsible AI notice live |  |  |  |  |
| Retention process approved |  |  |  |  |
| Deletion request tested |  |  |  |  |
| Support intake tested |  |  |  |  |
| Escalation path tested |  |  |  |  |
| Abuse reporting tested |  |  |  |  |
| Consent recording verified |  |  |  |  |

## Controlled beta results

| Metric / evidence | Approved target | Observed result | Window | Owner | Accepted |
|---|---|---|---|---|---|
| Invited testers |  |  |  |  |  |
| Active testers |  |  |  |  |  |
| Critical journey pass rate |  |  |  |  |  |
| API availability |  |  |  |  |  |
| Frontend availability |  |  |  |  |  |
| API latency |  |  |  |  |  |
| Error rate |  |  |  |  |  |
| Per-user AI cost |  |  |  |  |  |
| Aggregate AI cost |  |  |  |  |  |
| Support response time |  |  |  |  |  |
| Severity-1 defects | 0 |  |  |  |  |
| Unresolved severity-2 defects | 0 |  |  |  |  |

## Incidents and defects

Use restricted records for private details. Link only redacted references here.

| ID | Severity | Journey | Owner | Status | Fix reference | Verification reference |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Final acceptance

- all mandatory artifacts present: yes / no
- release SHA and image digests match: yes / no
- staging accepted: yes / no
- production controls accepted: yes / no
- policies and support live: yes / no
- controlled beta exit criteria met: yes / no
- severity-1 defects open: yes / no
- severity-2 defects open: yes / no
- final decision: GO / CONDITIONAL GO / NO-GO
- decision record reference:
- decision date:
- final owner:
