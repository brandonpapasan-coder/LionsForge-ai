# LionsForge AI Launch Operator Checklist

Parent epic: #400

This checklist coordinates external launch work. It does not state that any live environment, beta, or public launch exists.

## Release record

Record the approved source revision, backend build reference, frontend build reference, validation runs, selection date, and approving owner in the restricted operations record.

Deployment is blocked until all release references match.

## Accountable roles

Assign a primary and backup for:

- release command;
- infrastructure;
- database recovery;
- security review;
- privacy and legal review;
- customer support;
- incident command;
- AI cost control;
- product acceptance;
- final business approval.

## Environment readiness

For staging and production, record restricted-system references for:

- compute environment and namespace;
- database service;
- public web and service endpoints;
- domain and certificate ownership;
- protected GitHub environment configuration;
- image access;
- acceptance accounts;
- monitoring workspace;
- backup location;
- isolated recovery target.

Do not place private access material or tester information in repository files or public issues.

## Operating limits

Approve and record:

- tester cap;
- per-user daily request cap;
- aggregate daily AI spending limit;
- warning and shutdown thresholds;
- timeout and retry behavior;
- abuse threshold;
- concurrency cap;
- support response target;
- incident response target;
- maintenance and emergency-stop owners.

## Public readiness

Before registration opens, approve the public privacy, terms, responsible-use, retention, deletion, support, acceptable-use, and consent processes. Record approvers and effective dates in the restricted operations record.

## Execution sequence

1. Complete staging provisioning and acceptance under #29.
2. Deploy the approved release references.
3. Verify critical journeys, recovery, rollback, and monitoring.
4. Complete production controls under #401.
5. Complete policy and support readiness under #402.
6. Approve beta limits, owners, support coverage, and stop conditions.
7. Run the repository beta preflight.
8. Execute the controlled beta runbook under #403.
9. Capture redacted evidence in the launch evidence register.
10. Record GO, CONDITIONAL GO, or NO-GO with all required sign-offs.

## Immediate stop conditions

Pause deployment or beta access for any severe incident, unresolved critical journey defect, privacy or user-isolation failure, failed recovery or rollback, monitoring blind spot, sustained cost or abuse breach, approval withdrawal, or release-reference mismatch.

No trading, brokerage, portfolio execution, or market-order functionality is part of this launch scope.
