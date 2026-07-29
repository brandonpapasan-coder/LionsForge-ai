# Public Operations Activation Binding

This record binds a public-operations activation decision to one exact release candidate and the byte-level digest plus deterministic aggregate evidence digest of a validated public-operations evidence manifest.

The validator preserves the existing public-operations activation policy gate and adds a separate cryptographic control. It rejects unknown keys, unsafe paths, symlinks, malformed or mismatched digests, candidate drift, decision drift, aggregate-evidence drift, conflicting approval roles, invalid or future authorization timestamps, secret-like keys, and inconsistent decision or activation-mode combinations.

The committed example remains `NO-GO` with activation mode `NONE`. Its zero digests are structural placeholders and cannot pass byte verification until replaced with actual values from a same-candidate evidence manifest.

For an execution record, first validate the public-operations evidence manifest for the exact protected-`main` candidate. Record the manifest file SHA-256 and reported aggregate evidence SHA-256, use separate authorization and independent-approval roles, and then run the manual **Public Operations Activation Binding** workflow.

A valid result proves repository evidence binding and authorization-record consistency only. It does not activate public operations, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
