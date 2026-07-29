# Public Operations Evidence Reconciliation

This control validates the complete repository evidence chain for one exact protected-main candidate. It binds the public-operations evidence manifest, activation binding, activation receipt, and append-only receipt ledger by path and SHA-256.

The validator requires one consistent candidate SHA, decision, activation mode, aggregate evidence digest, authorization digest, receipt identifier, and exactly one matching ledger entry. It rejects unknown keys, unsafe paths, symlinks, malformed or mismatched digests, missing files, candidate drift, decision drift, activation-mode drift, aggregate-evidence drift, receipt drift, ledger omission, duplicate matching ledger entries, and secret-like keys.

The committed example is intentionally `NO-GO` with activation mode `NONE` and zero digests. It is structural only and cannot pass byte verification.

For a real reconciliation record, first validate each source artifact independently. Record the lowercase SHA-256 of the exact manifest, binding, receipt, and ledger bytes; copy the shared candidate, decision, activation mode, aggregate evidence digest, authorization digest, and receipt ID; then run the manual **Public Operations Evidence Reconciliation** workflow against the exact protected-main candidate.

A valid reconciliation proves repository evidence consistency only. It does not deploy software, enable public registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
