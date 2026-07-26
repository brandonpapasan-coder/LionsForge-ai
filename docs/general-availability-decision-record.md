# General Availability Decision Record

Issue: #566  
Launch epic: #400

Complete this record using non-secret evidence identifiers only. Do not include credentials, private tester identities, prompts, research content, support-record contents, deletion-request contents, answer keys, or hidden assessment metadata.

A completed record is evidence for review only. It does not authorize launch by itself.

## Release identity

- Release SHA:
- Previous rollback SHA:
- Backend image digest:
- Frontend image digest:
- Deployment environment:
- Proposed GA date/time (UTC):
- Release owner:
- Operations owner:

## Upstream acceptance evidence

- Production acceptance evidence:
- Public-operations activation evidence:
- Controlled-beta acceptance evidence:
- Candidate ancestry evidence:
- Running backend digest evidence:
- Running frontend digest evidence:

## Launch controls

- Registration mode:
- Maximum registered users:
- Per-user daily AI request limit:
- Aggregate daily AI budget (USD):
- Abuse threshold:
- Support owner:
- Incident owner:
- Privacy owner:
- Security owner:
- Rollback authority:

## Critical exit gates

- [ ] Production acceptance is approved for this exact release and image digests
- [ ] Public policies, consent, deletion, retention, support, abuse, and security-reporting workflows are live
- [ ] Controlled beta completed on this exact release candidate or an explicitly validated successor
- [ ] Running backend and frontend image digests match the approved immutable digests
- [ ] Backup and isolated restore evidence is current
- [ ] Rollback evidence is current
- [ ] Monitoring and launch-critical alerts are verified
- [ ] Registration, usage, abuse, and budget limits are enforced
- [ ] Support and incident owners are on duty
- [ ] No unresolved severity-1 or severity-2 incidents remain
- [ ] No unresolved critical or high-severity defects remain
- [ ] No expired exception remains open

Evidence links or identifiers:

## Operational evidence

| Control | Result | Evidence | Owner / follow-up |
| --- | --- | --- | --- |
| HTTPS API and web availability |  |  |  |
| Authentication and session recovery |  |  |  |
| Owner isolation and privacy |  |  |  |
| Investigation, claims, and evidence workflow |  |  |  |
| Validation and provenance workflow |  |  |  |
| Education and adaptive assessment |  |  |  |
| Mentor provider-failure behavior |  |  |  |
| Account deletion and retention workflow |  |  |  |
| Support and abuse-reporting workflow |  |  |  |
| Security-reporting workflow |  |  |  |
| Monitoring and alert delivery |  |  |  |
| Rollback exercise |  |  |  |
| Isolated restore verification |  |  |  |
| Budget-threshold enforcement |  |  |  |

## Controlled-beta and launch measurements

- Beta active users:
- Peak concurrent users:
- Availability:
- API latency summary:
- Frontend latency summary:
- Error-rate summary:
- AI requests:
- AI cost total (USD):
- AI cost per active user (USD):
- Support reports:
- Severity-1 incidents:
- Severity-2 incidents:
- Unresolved critical defects:
- Unresolved high-severity defects:
- Other unresolved defects:
- Open exceptions:
- Expired exceptions:

## Risks, exceptions, and blockers

Document every open exception with owner, mitigation, and expiration date. Do not include private user or support content.

- Open-risk summary:
- Exception register evidence:
- Blocker rationale:
- Blocker owner:

## Approvals

- Legal approval:
- Privacy approval:
- Security approval:
- Operations approval:
- Support approval:
- Product approval:
- Executive owner approval:

## Decision

Select exactly one:

- [ ] GO — all mandatory GA exit criteria are satisfied for the exact release candidate.
- [ ] NO-GO — one or more launch-critical criteria are not satisfied.

Decision rationale:

- Decision owner:
- Decision date/time (UTC):

A GO decision in this record remains subject to independent verification of live evidence and the authorization process defined by issues #29, #400, #401, #402, #403, and #461.