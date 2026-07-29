# Public Operations Activation Binding Receipt

This receipt binds one exact protected-main candidate to one exact public-operations activation-binding record. It records the binding file SHA-256, aggregate evidence SHA-256, decision, activation mode, unique receipt identifier, issuer role, issuance time, expiry time, and a deterministic authorization digest.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or mismatched digests, candidate drift, decision drift, activation-mode drift, aggregate-evidence drift, future issuance, invalid expiry ordering, expired GO receipts, conflicting GO issuer and authorization-owner roles, secret-like keys, and receipt identifiers already present in an optional prior-receipt ledger.

The committed example remains `NO-GO` with activation mode `NONE`. Its zero digests are structural placeholders and cannot pass byte or authorization-digest verification.

For an execution receipt, first validate the exact-candidate public-operations activation-binding record. Compute its lowercase SHA-256, copy its aggregate evidence digest, choose a unique receipt identifier, use an issuer role separate from the authorization owner for GO, calculate the deterministic authorization digest, and run the manual **Public Operations Activation Binding Receipt** workflow. Supply a prior receipt ledger when available to reject identifier replay.

A valid result proves repository receipt integrity and replay checks only. It does not activate public operations, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.