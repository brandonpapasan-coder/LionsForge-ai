# Public Operations Witness-Ledger Checkpoint

This control binds one exact append-only checkpoint-ledger witness receipt ledger to a signed, replay-resistant checkpoint for one exact protected-main candidate.

The validator binds the witness ledger by repository-relative path and exact SHA-256, preserves `NO-GO` and `VALID-NO-GO`, and verifies the ledger digest, entry count, terminal entry digest, checkpoint sequence, previous-checkpoint link, signer role, signer key identifier, approved signature algorithm, detached signature digest, distinct nonce digest, issue time, and bounded expiry.

Checkpoint sequence one must use the all-zero previous-checkpoint digest. Later checkpoints must provide a nonzero previous digest. Checkpoints must use the independent witness-ledger checkpoint signer role, approved Ed25519 or ECDSA P-256 metadata, a non-future issue time, and a validity window no longer than 30 days.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate identity material, candidate or state drift, source-byte or ledger-digest drift, entry-count or terminal-entry drift, invalid sequence links, invalid signer metadata, unsupported algorithms, future issuance, invalid expiry ordering, excessive validity windows, expired checkpoints, malformed source JSON, and secret-like keys.

The committed example is structural only and cannot pass validation because its required digests are zero and its timestamps are expired.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only that the checkpoint and referenced witness ledger were internally consistent at validation time. It does not verify a cryptographic signature, deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
