# Public Operations Validation

Tracks #402.

This procedure validates whether LionsForge AI is ready to enable public registration from a legal, privacy, support, retention, deletion, and operational-readiness perspective. It is an internal launch-control procedure and is not legal advice.

Public registration must remain disabled unless the completed activation record passes both validators, the exact-SHA release gates pass, and the final decision is **GO**.

## Required repository artifacts

- `docs/public-operations-activation-record.md`
- `scripts/validate_public_operations_activation.py`
- `scripts/validate_public_operations_row_evidence.py`
- `scripts/verify_release_gates.py`
- `backend/tests/test_public_operations_activation_validator.py`
- `backend/tests/test_public_operations_row_evidence_validator.py`
- `backend/tests/test_public_operations_activation_template.py`
- `backend/tests/test_verify_release_gates.py`
- `.github/workflows/public-operations-validate.yml`
- `.github/workflows/backend-ci.yml`

## Required release evidence

The release SHA must be an exact 40-character lowercase commit SHA that is contained in `main`.

The following workflows must have completed successfully for that exact SHA as `push` events on `main`:

- Backend CI
- Frontend CI
- Security Gate
- Deployment Validation

Each gate must also come from its exact required workflow file. A different workflow that reuses the same displayed name is not acceptable evidence.

Manual runs, pull-request runs, branch aliases, tags, shortened SHAs, and evidence from a different commit are not acceptable substitutes.

The release-gate verifier treats malformed GitHub API responses, unexpected non-JSON media types, malformed JSON, timeouts, truncated reads, unreadable response headers, non-object run entries, invalid or duplicate run IDs, repeated pagination evidence, and pagination beyond the configured safety limit as blocking errors. These conditions must not be interpreted as successful or merely absent evidence.

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

Any `PENDING`, `NOT VERIFIED`, `NOT TESTED`, `NOT APPROVED`, unresolved exception, missing evidence reference, mismatched release SHA, non-affirmative mandatory approval, malformed date, invalid date order, or final `NO-GO` decision keeps public registration disabled.

## Row-level evidence rules

The row-evidence validator independently enforces:

- policy effective dates use valid `YYYY-MM-DD` values and do not begin after the intended effective date
- channel test-evidence references are present and are not placeholders
- workflow test dates use valid `YYYY-MM-DD` values and are not later than the record review date
- workflow evidence references are present and are not placeholders
- final approval dates use valid `YYYY-MM-DD` values and are not later than the record review date

Repository-visible references must contain only non-sensitive identifiers. Detailed or sensitive evidence must remain in controlled internal systems.

## Template contract

The activation template contract test verifies that the repository template remains fail-closed, retains every mandatory row, documents the required date and evidence rules, and is rejected by both validators until operators replace all placeholder values with completed evidence.

## Local validation

Run both validators:

```bash
python scripts/validate_public_operations_activation.py \
  docs/public-operations-activation-record.md

python scripts/validate_public_operations_row_evidence.py \
  docs/public-operations-activation-record.md
```

A fully valid completed record produces both messages:

```text
VALID: public operations activation record is internally complete
VALID: public operations row evidence is internally complete
```

Either validator exiting nonzero blocks activation.

## GitHub Actions validation

Run the **Public Operations Validate** workflow with:

- `record_path`: `docs/public-operations-activation-record.md`
- `release_sha`: the exact 40-character release commit SHA

The workflow:

1. validates the inputs and path safety
2. verifies the release SHA belongs to `main`
3. confirms the activation record contains the same SHA
4. verifies exact-SHA required release-gate evidence
5. validates activation-record structure and decisions
6. validates row-level dates and evidence references
7. publishes both validator outcomes in the workflow summary
8. uploads release-gate and validator evidence with 90-day retention

A successful workflow run verifies repository evidence and record consistency only. It does not independently prove that external support mailboxes are monitored, deletion occurred in a live environment, legal review was performed, a public or registered-agent address is valid, or production infrastructure behaves as recorded. Those facts require separate controlled evidence.

## Decision rule

Set the activation record decision to **GO** only when all mandatory fields, affirmative approvals, tests, row-level dates, release gates, and evidence references are complete and accurate.

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
