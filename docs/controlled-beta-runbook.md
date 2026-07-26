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

## Validate the acceptance record

Complete a private working copy of `docs/controlled-beta-acceptance-record.md` using non-secret evidence identifiers only, then run:

```bash
python scripts/validate_controlled_beta_acceptance.py path/to/completed-controlled-beta-record.md
```

The command exits `0` only when the Markdown is internally complete and consistent. It fails closed on malformed release identity, blank owners or measurements, unchecked entry gates, missing journey or resilience evidence, unsupported result values, invalid counts, contradictory decisions, multiple selected decisions, and apparent credentials or prohibited private content.

A `VALID` result confirms record structure and internal consistency only. It does not prove that linked evidence is true, current, sufficient, independently verified, or tied to the live environment. It does not authorize controlled beta, public registration, payment collection, or general availability. Issues #29, #400, #401, #402, #403, and #461 remain governed by their live external evidence requirements.

## Validate the separate GA decision record

After controlled beta, complete a private working copy of `docs/general-availability-decision-record.md` using non-secret evidence identifiers only, then run:

```bash
python scripts/validate_general_availability_decision.py path/to/completed-ga-decision-record.md
```

The command exits `0` only when the record binds one exact release and rollback SHA to immutable image digests, upstream acceptance evidence, checked exit gates, passed operational controls, valid launch measurements, complete approvals, and exactly one internally consistent `GO` or `NO-GO` decision.

A `VALID` GA record confirms Markdown completeness and internal consistency only. It does not independently verify live infrastructure, evidence freshness, ownership, production state, or authorization. It does not enable public registration, payment collection, production changes, or general availability. The external gate issues remain authoritative and fail closed.

## Validate the complete launch evidence chain

After each standalone record validates, cross-check the four non-secret working copies together:

```bash
python scripts/validate_launch_evidence_chain.py \
  path/to/completed-production-record.md \
  path/to/completed-public-operations-record.md \
  path/to/completed-controlled-beta-record.md \
  path/to/completed-ga-decision-record.md
```

The chain validator invokes every standalone validator and then checks release and rollback identity, immutable image digests, public-operations candidate binding, documented candidate ancestry, distinct upstream evidence identifiers, and decision ordering. A differing beta predecessor is accepted only when the GA record contains an explicit candidate-ancestry evidence identifier; a matching release SHA with different digests or rollback identity is rejected as ambiguous.

A `VALID` chain means only that the supplied Markdown records are individually valid and mutually consistent. It does not establish evidence truth or freshness, confirm live infrastructure, authorize deployment or payment collection, enable registration, or declare controlled beta or general availability. The external gate issues remain authoritative and fail closed.
