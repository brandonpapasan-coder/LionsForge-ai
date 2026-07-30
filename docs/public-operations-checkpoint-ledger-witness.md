# Public Operations Checkpoint-Ledger Witness Receipt

This control binds one exact append-only public-operations checkpoint ledger to a replay-resistant independent witness receipt for one exact protected-main candidate.

The validator binds the checkpoint ledger by repository-relative path and exact SHA-256, preserves `NO-GO` and `VALID-NO-GO`, verifies the checkpoint-ledger digest, entry count, terminal entry digest, witness receipt identifier, witness role, witness key identifier, approved signature algorithm, detached signature digest, distinct nonce digest, issue time, and bounded expiry.

Witness receipts must use the independent checkpoint-ledger witness role, approved Ed25519 or ECDSA P-256 signature metadata, a nonzero nonce distinct from the ledger, terminal-entry, and signature digests, a non-future issue time, and a validity window no longer than 30 days.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate identity material, candidate or state drift, checkpoint-ledger byte or digest drift, entry-count or terminal-entry drift, invalid witness metadata, unsupported algorithms, future issuance, invalid expiry ordering, excessive validity windows, expired receipts, malformed source JSON, and secret-like keys.

The committed example is structural only and cannot pass validation because its required digests are zero and its timestamps are expired.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only that the independent witness receipt and referenced checkpoint ledger were internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
