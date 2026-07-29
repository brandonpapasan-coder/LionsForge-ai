# Public Operations Freshness Ledger Checkpoint

This control anchors one exact append-only public-operations freshness receipt ledger into a rollback-resistant checkpoint for one exact protected-main candidate.

The validator binds the ledger by repository-relative path and exact SHA-256, preserves `NO-GO` and `VALID-NO-GO`, verifies the ledger digest, entry count, terminal entry digest, checkpoint sequence, prior checkpoint link, signer role, key identifier, approved signature algorithm, detached signature digest, and non-future RFC3339 UTC issue time.

A checkpoint sequence must increase beyond the last accepted sequence. The first checkpoint uses a zero previous-checkpoint digest; every later checkpoint requires the exact prior checkpoint digest. This detects rollback, truncation, substitution, and broken checkpoint chains.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate digest material, candidate or state drift, ledger digest drift, entry-count drift, terminal-entry drift, sequence rollback, broken links, invalid signer or key metadata, unsupported algorithms, future timestamps, malformed source ledgers, and secret-like keys.

The committed example is structural only and cannot pass validation because its required digests are zero and the referenced structural ledger is not a valid checkpoint source.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only that the checkpoint metadata and referenced ledger were internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
