# Public Operations Checkpoint Ledger

This control validates an append-only ledger of signed public-operations freshness checkpoints for one exact protected-main candidate.

Each entry binds one exact checkpoint file by repository-relative path and SHA-256, preserves `NO-GO` and `VALID-NO-GO`, verifies checkpoint and ledger digests, entry count, terminal entry digest, signer role, key identifier, signature algorithm, detached signature digest, issue time, prior-entry link, and deterministic entry digest.

Checkpoint sequences must be contiguous from one. Source paths and checkpoint digests must be unique. Issue times must increase monotonically. The signer role, key identifier, and signature algorithm must remain stable throughout one ledger, making unexpected signing-identity changes fail closed.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate paths or checkpoint digests, sequence gaps, broken links, candidate or state drift, ledger or terminal drift, signer/key/algorithm drift, non-monotonic timestamps, malformed source checkpoints, invalid entry digests, and secret-like keys.

The committed example is structural only and cannot pass validation because its required digests are zero and its entry digest is not derived from the entry material.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only that the checkpoint chain was internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
