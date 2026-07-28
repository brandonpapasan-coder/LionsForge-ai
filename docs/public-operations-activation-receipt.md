# Public Operations Activation Receipt

Use this control only after the public-operations activation record is complete and the existing validator reports `VALID`.

## Purpose

The receipt binds one validated activation record to one exact protected-main release candidate. It records the canonical source SHA-256 digest, canonical byte length, final `GO` decision, schema and generator versions, and generation timestamp.

The receipt proves integrity and candidate binding only. It does not perform legal review, test support or escalation channels, verify public URLs, approve payments, or authorize public registration, controlled beta, production billing, or general availability.

## Local generation

```bash
python scripts/manage_public_operations_activation_receipt.py generate \
  docs/public-operations-activation-record.md \
  --candidate-sha <40-character-main-sha> \
  --generated-at <UTC-timestamp-ending-in-Z> \
  --output public-operations-activation-receipt.json
```

## Independent verification

```bash
python scripts/manage_public_operations_activation_receipt.py validate \
  public-operations-activation-receipt.json \
  --record docs/public-operations-activation-record.md \
  --expected-candidate-sha <40-character-main-sha>
```

Verification fails when the source record changes, the candidate is substituted, metadata is malformed, the underlying activation record no longer validates, or prohibited secret-bearing field terms are present.

## GitHub Actions

Dispatch **Public Operations Activation Receipt** with:

- the fresh exact release-candidate SHA currently contained in protected `main`
- the repository-relative path to the completed activation record

The workflow checks out the exact candidate, verifies `HEAD`, verifies protected-main ancestry, validates the source record, generates the receipt, revalidates it against the same source and candidate, and retains the JSON artifact for 90 days.

## Data handling

Do not include secrets, credentials, private support conversations, tester identities, request contents, uploaded evidence, or personal staff addresses in the record or receipt. Use controlled evidence references and public operational roles instead.
