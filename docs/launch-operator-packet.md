# LionsForge AI Launch Operator Packet

Parent epic: #400  
Staging blocker: #29  
Production blocker: #401  
Legal and support blocker: #402  
Controlled beta blocker: #403

This packet converts the remaining external launch work into an operator-owned execution sequence. It does not claim that staging, production, beta, or general availability is live.

## 1. Release candidate

Record one exact 40-character commit from `main`.

- release commit reference:
- selection date:
- selected by:
- Backend CI run:
- Frontend CI run:
- Security Gate run:
- Deployment Validation run:
- backend immutable image digest:
- frontend immutable image digest:

Do not approve deployment when the commit reference and both immutable image digests are missing.

## 2. Named owners

Every role must name a person or accountable team before launch execution begins.

| Responsibility | Owner | Backup | Contact path | Approved |
|---|---|---|---|---|
| Release commander |  |  |  |  |
| Infrastructure |  |  |  |  |
| Database and restore |  |  |  |  |
| Security and access |  |  |  |  |
| Privacy and legal |  |  |  |  |
| Support |  |  |  |  |
| Incident commander |  |  |  |  |
| AI budget and provider |  |  |  |  |
| Product acceptance |  |  |  |  |
| Final business owner |  |  |  |  |

## 3. Infrastructure intake

Record references only. Never paste authentication material, cluster configuration content, provider credentials, signing material, acceptance-user credentials, or private customer data into this document or a public issue.

### Staging

- Kubernetes cluster and namespace reference:
- PostgreSQL instance reference:
- API HTTPS endpoint reference:
- web HTTPS endpoint reference:
- DNS owner:
- certificate status:
- GitHub `staging` environment configured:
- image-pull access verified:
- acceptance account stored in approved secret manager:
- observability workspace:
- backup location:
- restore target:

### Production / controlled beta

- Kubernetes cluster and namespace reference:
- PostgreSQL instance reference:
- API HTTPS endpoint reference:
- web HTTPS endpoint reference:
- DNS owner:
- certificate status:
- GitHub `production` environment configured:
- image-pull access verified:
- admin account stored in approved secret manager:
- beta acceptance account stored in approved secret manager:
- observability workspace:
- backup location:
- isolated restore target:

## 4. Required non-secret configuration

- approved tester cap:
- per-user daily AI request limit:
- aggregate daily AI budget:
- budget warning threshold:
- budget stop threshold:
- request timeout:
- retry policy:
- abuse-rate threshold:
- maximum concurrent users:
- support response target:
- incident response target:
- maintenance-mode owner:
- emergency shutdown owner:

## 5. Policy and support approval

Record the approved public references and effective dates.

| Requirement | Public reference | Effective date | Approver | Status |
|---|---|---|---|---|
| Privacy policy |  |  |  |  |
| Terms of service |  |  |  |  |
| Responsible AI / research-use notice |  |  |  |  |
| Data retention policy |  |  |  |  |
| Account deletion process |  |  |  |  |
| Support process |  |  |  |  |
| Acceptable-use and abuse reporting |  |  |  |  |
| Cancellation/refund terms, if payments are enabled |  |  |  |  |
| Analytics/cookie consent, where applicable |  |  |  |  |

Public registration must remain disabled until required approvals are complete.

## 6. Execution order

1. Complete staging provisioning in #29.
2. Deploy the selected commit by immutable backend and frontend digests.
3. Execute staging acceptance and record evidence.
4. Complete production controls in #401.
5. Complete legal, privacy, and support activation in #402.
6. Approve tester count, quotas, budget, support coverage, and stop thresholds.
7. Run `scripts/beta-preflight.sh` using approved non-secret values.
8. Execute the controlled beta runbook in `docs/controlled-beta-runbook.md`.
9. Record every required artifact in `docs/launch-evidence-register.md`.
10. Complete the GO, CONDITIONAL GO, or NO-GO decision.

Do not skip staging acceptance or infer production readiness from repository CI alone.

## 7. Immediate stop conditions

Pause deployment or beta access for:

- a severity-1 incident;
- an unresolved severity-2 defect on a critical journey;
- authorization, privacy, or user-isolation failure;
- missing or invalid backup, restore, or rollback evidence;
- an unmonitored launch-critical service;
- sustained abuse, budget, or provider-limit breach;
- withdrawal of legal, security, operations, or owner approval;
- mismatch between deployed commit or image digests and the approved release record.

## 8. Final decision record

- decision: GO / CONDITIONAL GO / NO-GO
- release commit reference:
- decision date:
- approved beta or GA scope:
- conditions, if any:
- unresolved severity-3 or lower defects:
- rollback target:
- next review date:

Sign-off:

- release commander:
- infrastructure:
- security:
- privacy/legal:
- support:
- product:
- final business owner:
