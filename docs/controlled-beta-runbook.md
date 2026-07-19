# LionsForge AI Controlled Beta Runbook

Parent workstream: #403  
Launch epic: #400

This runbook defines the controlled-beta procedure. It does not authorize a beta by itself. Live execution requires approved infrastructure, policy contacts, quotas, budget thresholds, and named operators.

## Entry criteria

- staging acceptance is complete with immutable backend and frontend digests recorded;
- production infrastructure and release controls are accepted;
- Privacy, Terms, Responsible AI, Support, deletion, and retention processes are approved and live;
- one exact 40-character `main` SHA is selected for the beta;
- no unresolved severity-1 or severity-2 defects exist;
- support and incident owners are on duty;
- registration cap, per-user request limit, aggregate AI budget, and stop thresholds are approved;
- backup, restore, rollback, monitoring, and alerting have current evidence.

## Access control

Use invitation-only access or an enforced registration cap. Do not enable unrestricted public registration during the controlled beta.

Record:

- approved maximum tester count;
- invitation owner and invitation source;
- accepted tester count;
- disabled, rejected, or removed accounts;
- the mechanism that blocks registrations after the cap is reached.

## Required limits

Configure and verify:

- per-user daily AI request limit;
- aggregate daily AI budget;
- request timeout and retry policy;
- abuse-rate threshold;
- maximum concurrent beta users;
- emergency disable or maintenance-mode procedure.

Limit values are operational configuration and must not be committed with credentials or private tester data.

## Preflight

Export the approved non-secret values and run:

```bash
BETA_RELEASE_SHA=<40-char-main-sha> \
BETA_API_URL=https://<beta-api-host> \
BETA_WEB_URL=https://<beta-web-host> \
BETA_MAX_USERS=<positive-integer> \
BETA_DAILY_AI_BUDGET_USD=<positive-amount> \
BETA_PER_USER_DAILY_REQUEST_LIMIT=<positive-integer> \
BETA_SUPPORT_OWNER=<named-owner> \
BETA_INCIDENT_OWNER=<named-owner> \
./scripts/beta-preflight.sh
```

## Critical user journeys

Capture pass/fail evidence for:

1. invitation or approved registration;
2. authentication and session recovery;
3. investigation creation and private access control;
4. claim and evidence creation;
5. validation-state review and provenance history;
6. education recommendations and adaptive assessment;
7. Mentor interaction with safe provider-failure behavior;
8. account support request;
9. privacy or deletion request intake;
10. logout and revoked-access behavior.

No answer keys, hidden assessment internals, credentials, or private tester content may be stored in evidence records.

## Failure and resilience exercises

Exercise and record:

- AI provider timeout;
- AI provider unavailable response;
- API outage alert;
- frontend outage alert;
- database connectivity failure alert;
- elevated error-rate alert;
- budget threshold alert;
- rollback to the approved previous SHA;
- backup restoration to an isolated verification target.

## Feedback and incidents

Use structured, access-controlled records containing:

- report identifier;
- timestamp;
- affected journey;
- severity;
- reproducibility;
- expected and observed behavior;
- owner;
- disposition;
- linked fix and validation evidence.

Do not place tester email addresses, prompts, research content, or other private data in public issues.

## Stop conditions

Pause the beta immediately when any of the following occurs:

- severity-1 incident;
- unresolved severity-2 incident affecting a critical journey;
- privacy, authorization, or data-isolation failure;
- inability to restore or roll back;
- sustained budget or abuse threshold breach;
- legal or policy withdrawal of approval;
- monitoring blind spot affecting a launch-critical service.

## Exit criteria

A general-availability recommendation requires:

- all critical journeys passed on the accepted release SHA;
- no unresolved severity-1 or severity-2 defects;
- effective registration, usage, and abuse controls;
- AI cost remained within approved per-user and aggregate thresholds;
- support and incident response met approved service targets;
- deletion, retention, backup, restore, and rollback evidence is current;
- final legal, security, operations, product, and owner sign-off;
- a completed GO, CONDITIONAL GO, or NO-GO record.
