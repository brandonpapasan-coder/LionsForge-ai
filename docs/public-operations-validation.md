# Public Operations Validation

Tracks #402.

This procedure validates whether LionsForge AI is ready to enable public registration from a legal, privacy, support, retention, deletion, and operational-readiness perspective. It is an internal launch-control procedure and is not legal advice.

Public registration must remain disabled unless the completed activation record validates successfully and the final decision is **GO**.

## Required repository artifacts

- `docs/public-operations-activation-record.md`
- `scripts/validate_public_operations_activation.py`
- `scripts/verify_release_gates.py`
- `.github/workflows/public-operations-validate.yml`

## Required release evidence

The release SHA must be an exact 40-character lowercase commit SHA that is contained in `main`.

The following workflows must have completed successfully for that exact SHA as `push` events on `main`:

- Backend CI
- Frontend CI
- Security Gate
- Deployment Validation

Manual runs, pull-request runs, branch aliases, tags, shortened SHAs, and evidence from a different commit are not acceptable substitutes.

## Activation record requirements

The activation record must include:

- approved policy versions and effective dates
- the approved public legal entity name
- a public business address or approved registered-agent address; never record a private home address
- governing-law and venue language explicitly approved
- supported launch jurisdictions and an approved age-eligibility position
- monitored public support, privacy, security, and abuse-reporting channels
- approved retention and deletion behavior for every required data class
- passed account closure, deletion, support, abuse, security, and consent workflows
- completed privacy, logging, analytics, and consent-control decisions
- zero open High or Critical privacy or security defects
- final approvals from business, legal, privacy, security, support operations, and release owners
- a release candidate SHA matching the exact build being reviewed

The final `Decision` field must be `GO`. A complete record that remains marked `NO-GO` does not pass activation validation.

Approval fields must express affirmative approval, not merely contain text. For example, `Governing-law and venue language approved` must record an affirmative approved value rather than `NO`, `PENDING`, or an unresolved exception.

Consent controls must be explicit:

- use `YES` when consent controls are required, and record successful testing as `YES`, `VERIFIED`, or `PASSED`
- use `NO` or `NOT REQUIRED` only when the approved legal/privacy position supports that decision
- record `NOT APPLICABLE`, `YES`, `VERIFIED`, or `PASSED` for the corresponding testing-status field when consent is not required

Any `PENDING`, `NOT VERIFIED`, `NOT TESTED`, `NOT APPROVED`, unresolved exception, missing evidence reference, mismatched release SHA, non-affirmative mandatory approval, or final `NO-GO` decision keeps public registration disabled.

## Local validation

Run:

```bash
python scripts/validate_public_operations_activation.py \
  docs/public-operations-activation-record.md
```

A valid completed record exits with status `0` and prints:

```text
VALID: public operations activation record is internally complete
```

An incomplete or inconsistent record exits nonzero and prints one or more findings.

## GitHub Actions validation

Run the **Public Operations Validate** workflow with:

- `record_path`: `docs/public-operations-activation-record.md`
- `release_sha`: the exact 40-character release commit SHA

The workflow:

1. validates the inputs and path safety
2. verifies the release SHA belongs to `main`
3. confirms the activation record contains the same SHA
4. verifies exact-SHA required release-gate evidence
5. validates the activation record
6. publishes a workflow summary
7. uploads validation evidence with 90-day retention

A successful workflow run verifies repository evidence and record consistency only. It does not independently prove that external support mailboxes are monitored, deletion occurred in a live environment, legal review was performed, a public or registered-agent address is valid, or production infrastructure behaves as recorded. Those facts require separate controlled evidence.

## Decision rule

Set the activation record decision to **GO** only when all mandatory fields, affirmative approvals, tests, release gates, and evidence references are complete and accurate.

Otherwise retain **NO-GO** and keep public registration disabled.

## Evidence handling

Do not commit:

- user personal data
- support request contents
- identity-verification documents
- credentials, tokens, or mailbox configuration
- private prompts or investigation content
- private home addresses

Use controlled internal references for sensitive evidence and record only non-sensitive identifiers in the repository.
