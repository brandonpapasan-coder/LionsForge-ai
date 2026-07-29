# Public Operations Freshness Receipt

This control binds one exact successful public-operations evidence freshness report into a replay-resistant receipt for one exact protected-main candidate.

The validator requires `NO-GO` and `VALID-NO-GO`, binds the source report by repository-relative path and exact SHA-256, verifies candidate and freshness-digest continuity, requires a unique receipt identifier, a distinct nonzero nonce digest, and an RFC3339 UTC issue time that is not in the future. It rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate identity material, candidate drift, state drift, digest drift, malformed source JSON, and secret-like keys.

The committed example is structural only and cannot pass validation because its digests are all zero and not distinct.

For a real receipt, independently validate the freshness report, record the SHA-256 of its exact bytes and its emitted freshness digest, create a unique non-secret receipt ID, hash a one-time non-secret nonce outside the repository, and run the manual **Public Operations Freshness Receipt** workflow against the same exact protected-main candidate.

A successful result is `VALID-NO-GO`. The receipt proves only that the referenced freshness report and receipt metadata were internally consistent at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
