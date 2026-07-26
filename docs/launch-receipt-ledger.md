# Launch receipt ledger

The launch receipt ledger is an append-only, non-secret audit index for canonical launch evidence-chain receipt files. It validates ordering and integrity relationships only.

A valid ledger does **not** prove that evidence is true, current, owned by the operator, deployed, or approved. It does not authorize staging, production, public registration, payment collection, controlled beta, or general availability. All existing release and operations gates remain fail-closed.

## Canonical format

```json
{
  "schema": "lionsforge.launch-receipt-ledger",
  "schema_version": 1,
  "validator_version": "1.0.0",
  "entries": [
    {
      "sequence": 1,
      "recorded_at": "2026-08-01T12:00:00Z",
      "receipt_sha256": "<64 lowercase hex characters>",
      "predecessor_receipt_sha256": null,
      "release_identity": "<40 lowercase hex commit SHA>",
      "status": "superseded",
      "reason": "Replaced by a newer immutable candidate",
      "owner": "release-operations"
    },
    {
      "sequence": 2,
      "recorded_at": "2026-08-02T12:00:00Z",
      "receipt_sha256": "<64 lowercase hex characters>",
      "predecessor_receipt_sha256": "<sequence 1 receipt digest>",
      "release_identity": "<different 40 lowercase hex commit SHA>",
      "status": "current",
      "reason": null,
      "owner": null
    }
  ]
}
```

Canonical JSON is UTF-8, sorted by key, compactly encoded, and terminated by one newline. Hash the exact receipt file bytes with SHA-256 before recording `receipt_sha256`.

## Ordering rules

- Sequence begins at `1`, has no gaps, and matches array order.
- Receipt digests and release identities are unique.
- UTC timestamps increase strictly.
- The first entry has a null predecessor.
- Every later entry references the immediately prior receipt digest.
- Exactly one entry is `current`, and it is the final entry.
- Every non-final entry is `superseded` or `revoked` with a nonblank reason and owner.
- Entries are never edited or deleted. Add a new final entry and change the previous current entry to `superseded` or `revoked` in the same reviewed change.

## Validate

```bash
python scripts/launch_receipt_ledger.py path/to/launch-receipt-ledger.json
```

Optionally bind a referenced receipt file to its recorded digest:

```bash
python scripts/launch_receipt_ledger.py path/to/launch-receipt-ledger.json \
  --receipt <sha256-digest>=path/to/launch-evidence-chain-receipt.json
```

The command exits `0` only when there are no findings. Findings are sorted deterministically and use stable codes. Any malformed, missing, unsupported, stale, replayed, forked, cyclic, privacy-sensitive, or inconsistent field fails closed.

## Privacy boundary

The ledger may contain only operational identifiers needed for audit ordering. Never include credentials, secrets, private keys, private tester identities, prompts, research content, support records, deletion-request contents, answer keys, or hidden assessment metadata. The validator rejects prohibited field names and text resembling credentials or private keys.

Store private operational evidence in the approved restricted system. The repository ledger should point only to non-secret canonical receipt digests and release identities.
