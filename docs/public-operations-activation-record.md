# Public Operations Activation Record

Tracks #402 and #450.

This record is operational evidence, not legal advice. It must not contain secrets, private mailbox credentials, personal user data, request contents, or non-public residential addresses. Public registration remains disabled until every required section is complete, the required exact-SHA release gates are independently verified, both repository validators succeed, and the final decision is **GO**.

## Record identity

- Release candidate SHA: `PENDING`
- Record owner role: `PENDING`
- Review date: `PENDING`
- Intended effective date: `PENDING`
- Decision: **NO-GO**

Use valid `YYYY-MM-DD` dates. The intended effective date must not be earlier than the review date. Any `PENDING`, `TODO`, `TBD`, `NOT VERIFIED`, `NOT TESTED`, unresolved exception, missing evidence reference, malformed date, or missing mandatory approval keeps the decision at **NO-GO**.

## Policy approvals

Policy effective dates must use `YYYY-MM-DD` and must not be later than the intended effective date.

| Surface | Version or SHA | Effective date | Business approver role | Legal approver role | Status |
|---|---|---|---|---|---|
| Privacy Notice | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |
| Terms of Service | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |
| Responsible AI disclosure | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |
| Data retention and deletion policy | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |
| Acceptable use and abuse reporting | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |
| Pricing, cancellation, and refund terms | NOT APPLICABLE OR PENDING | PENDING | PENDING | PENDING | NOT APPROVED |

## Legal entity and jurisdiction configuration

- Public legal entity name: `PENDING`
- Public business address or approved registered-agent address: `PENDING`
- Governing-law and venue language approved: `PENDING`
- Supported launch jurisdictions: `PENDING`
- Age eligibility and parental-consent position: `PENDING`
- Jurisdiction-specific privacy-rights matrix reference: `PENDING`
- Subprocessor and AI-provider disclosure reference: `PENDING`

Use non-sensitive controlled-record identifiers for evidence references. Do not place private home-address information in this repository.

## Monitored channels

Record aliases or public addresses only after they are approved for publication. Do not record credentials, tokens, forwarding rules, or private escalation phone numbers. Every required channel must include a non-placeholder test-evidence reference.

| Function | Public channel | Operational owner role | Monitoring verified | Test evidence reference |
|---|---|---|---|---|
| General support | PENDING | PENDING | NOT VERIFIED | PENDING |
| Privacy requests | PENDING | PENDING | NOT VERIFIED | PENDING |
| Security reports | PENDING | PENDING | NOT VERIFIED | PENDING |
| Abuse reports | PENDING | PENDING | NOT VERIFIED | PENDING |
| Billing support | NOT APPLICABLE OR PENDING | PENDING | NOT VERIFIED | PENDING |

## Retention configuration

| Data class | Approved retention period | Deletion or de-identification behavior | Backup exception | Approval status |
|---|---|---|---|---|
| Account records | PENDING | PENDING | PENDING | NOT APPROVED |
| Investigation and workspace data | PENDING | PENDING | PENDING | NOT APPROVED |
| Education and mastery history | PENDING | PENDING | PENDING | NOT APPROVED |
| Authentication and security logs | PENDING | PENDING | PENDING | NOT APPROVED |
| Application and provider logs | PENDING | PENDING | PENDING | NOT APPROVED |
| Backups | PENDING | PENDING | PENDING | NOT APPROVED |
| Support and privacy-request records | PENDING | PENDING | PENDING | NOT APPROVED |

## Workflow acceptance evidence

Evidence references may point to controlled internal records. Public GitHub issues must not contain request contents, identity documents, authentication data, or user-private material. Test dates must use `YYYY-MM-DD`, must not be later than the review date, and every required workflow must include a non-placeholder evidence reference.

| Workflow | Test date | Tester role | Evidence reference | Result |
|---|---|---|---|---|
| Privacy request intake | PENDING | PENDING | PENDING | NOT TESTED |
| Identity verification | PENDING | PENDING | PENDING | NOT TESTED |
| Account closure and authentication disablement | PENDING | PENDING | PENDING | NOT TESTED |
| Eligible data deletion or de-identification | PENDING | PENDING | PENDING | NOT TESTED |
| Backup-expiry handling | PENDING | PENDING | PENDING | NOT TESTED |
| General support intake and response | PENDING | PENDING | PENDING | NOT TESTED |
| Abuse report intake and escalation | PENDING | PENDING | PENDING | NOT TESTED |
| Security report intake and escalation | PENDING | PENDING | PENDING | NOT TESTED |
| Consent recording and policy-version capture | PENDING | PENDING | PENDING | NOT TESTED |
| Subscription cancellation and refund handling | NOT APPLICABLE OR PENDING | PENDING | PENDING | NOT TESTED |

## Operational targets

- Support response target: `PENDING`
- Privacy-request response target: `PENDING`
- Security-report acknowledgment target: `PENDING`
- Abuse-report acknowledgment target: `PENDING`
- After-hours critical incident coverage: `PENDING`
- Escalation owner role: `PENDING`
- Coverage gaps or accepted exceptions: `PENDING`

## Privacy and logging review

- Log-redaction review completed: `NO`
- Secrets and credentials excluded from logs: `NOT VERIFIED`
- Private prompts, evidence, education records, and support content excluded or minimized: `NOT VERIFIED`
- Analytics and cookie inventory completed: `NO`
- Consent control required: `PENDING`
- Consent control tested when required: `NOT TESTED`
- Open high or critical privacy/security defects: `PENDING`

## Final authorization

All approvers authorize only the capabilities actually implemented by LionsForge AI: research assistance, evidence validation, and education. No approval may imply trading, brokerage, portfolio execution, or market-order functionality. Approval dates must use `YYYY-MM-DD` and must not be later than the review date.

| Approval | Approver role | Date | Status |
|---|---|---|---|
| Business owner | PENDING | PENDING | NOT APPROVED |
| Legal reviewer | PENDING | PENDING | NOT APPROVED |
| Privacy owner | PENDING | PENDING | NOT APPROVED |
| Security owner | PENDING | PENDING | NOT APPROVED |
| Support operations owner | PENDING | PENDING | NOT APPROVED |
| Release owner | PENDING | PENDING | NOT APPROVED |

### Decision rule

Set the decision to **GO** only when:

1. Every mandatory policy is approved with a version and valid effective date.
2. Monitored channels and owners are verified with controlled test-evidence references.
3. Retention periods and deletion behavior are approved.
4. Required intake, deletion, escalation, and consent workflows pass with valid dates and evidence references.
5. No unresolved high or critical privacy, security, or support defect remains.
6. Payment terms are approved or payments are explicitly disabled.
7. Every final approver records affirmative approval with a valid date.
8. The release candidate SHA matches the exact commit reviewed by the activation workflow.
9. Required exact-SHA release gates and both public-operations validators succeed.
10. External legal and operational facts are separately confirmed through controlled evidence.

Until then, the decision remains **NO-GO** and public registration must remain disabled.
