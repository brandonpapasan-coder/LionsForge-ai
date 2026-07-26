# LionsForge AI Launch Receipt Ledger

This document defines the non-secret audit ledger used to order launch evidence-chain receipts. The ledger does not authorize staging, production, public registration, payment collection, controlled beta, or general availability.

## Canonical structure

The ledger is a JSON object with:

- `schema`: `lionsforge.launch-receipt-ledger`
- `schema_version`: `1`
- `entries`: a non-empty ordered array

Each entry contains:

- `sequence`: positive integer beginning at `1` with no gaps
- `receipt_sha256`: lowercase SHA-256 digest of one canonical receipt file
- `predecessor_sha256`: blank for the first entry; otherwise the immediately prior receipt digest
- `release_sha`: exact 40-character lowercase release SHA bound by the receipt
- `recorded_at`: ISO-8601 UTC timestamp
- `status`: `current`, `superseded`, or `revoked`
- `reason`: blank for the current entry; required for superseded or revoked entries
- `owner`: nonblank operational owner

Exactly one entry must be `current`, and it must be the final sequence entry. Every earlier entry must be `superseded` or `revoked` with a reason and owner.

## Validate ledger structure

```bash
python scripts/validate_launch_receipt_ledger.py path/to/launch-receipt-ledger.json
```

The validator fails closed on malformed JSON, unsupported schema or version, missing or extra fields, sequence gaps, duplicate sequence values, replayed receipt digests, predecessor forks, duplicate release identities, timestamp regression, invalid status transitions, missing owners or reasons, and apparent credentials or prohibited private content.

## Validate bound receipt files

Supply receipt files in the same sequence order as the ledger entries:

```bash
python scripts/validate_launch_receipt_ledger.py \
  path/to/launch-receipt-ledger.json \
  path/to/receipt-0001.json \
  path/to/receipt-0002.json
```

The validator recomputes each receipt file digest and compares the receipt's release identity with the ledger entry. Receipt substitution, modification, ordering mistakes, or release-identity drift fail closed.

A `VALID` result establishes only ledger structure, append-only ordering, and file-binding consistency. It does not prove that evidence is true, fresh, sufficient, independently verified, or tied to live infrastructure. Issues #29, #400, #401, #402, #403, and #461 remain authoritative and NO-GO until their external evidence requirements are completed.
