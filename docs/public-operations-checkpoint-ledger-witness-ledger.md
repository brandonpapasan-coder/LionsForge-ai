# Public Operations Checkpoint-Ledger Witness Receipt Ledger

This control validates an append-only ledger of independent checkpoint-ledger witness receipts for one exact protected-main candidate.

Each ledger entry binds one exact witness receipt by repository-relative path and SHA-256. The validator preserves `NO-GO` and `VALID-NO-GO`, verifies candidate continuity, source bytes, witness digest, checkpoint-ledger digest, entry count, terminal entry digest, receipt identity, witness identity, signature metadata, nonce, issue and expiry times, previous-entry link, and deterministic entry digest.

Sequences must be contiguous from one. Receipt paths, receipt identifiers, witness digests, and nonce digests must be unique. Issue times must increase monotonically. Witness role, key identifier, and signature algorithm must remain stable throughout one ledger.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate identities, sequence gaps, broken links, candidate or state drift, source-field drift, witness-identity drift, expired receipts, malformed source JSON, and secret-like keys.

The committed example is structural only and cannot pass because its required digests are zero and its source receipt is expired.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only that the witness-receipt history was internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
