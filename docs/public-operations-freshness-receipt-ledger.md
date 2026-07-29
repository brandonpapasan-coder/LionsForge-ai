# Public Operations Freshness Receipt Ledger

This control validates an append-only, hash-chained ledger of public-operations freshness receipts for one exact protected-main candidate.

Each entry binds one exact receipt file by repository-relative path and SHA-256, requires contiguous sequence numbers, preserves `NO-GO` and `VALID-NO-GO`, verifies receipt ID, nonce digest, receipt digest, issue time, and candidate continuity, and links to the prior entry digest. Receipt IDs, nonce digests, and receipt digests must be unique, and issue times must increase monotonically.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, candidate or state drift, receipt-field drift, duplicate identity material, sequence gaps, broken links, invalid entry digests, malformed source receipts, non-monotonic timestamps, and secret-like keys.

The committed example is structural only and cannot pass validation because its digests are zero and its entry digest is not derived from the entry material.

For a real ledger, independently validate every freshness receipt, append entries without changing prior entries, compute each entry digest from every entry field except `entry_digest`, and run the manual **Public Operations Freshness Receipt Ledger** workflow against the same exact protected-main candidate.

A successful result is `VALID-NO-GO`. It proves only that the recorded receipt chain was internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
