# Public Operations Evidence Manifest

This manifest binds one exact release candidate to the byte-level SHA-256 digests and declared decisions of four required public-operations records: the public data inventory, support and escalation readiness, privacy-request readiness, and incident-communication readiness.

The validator rejects unknown keys, unsafe paths, symlinks, duplicate or missing evidence types, malformed or mismatched digests, candidate drift, decision drift, secret-like keys, and GO manifests that do not require GO from every bound record.

The committed example is intentionally `NO-GO`. Its zero digests are placeholders demonstrating structure only and will fail byte verification until an operator replaces them with current SHA-256 values for exact-candidate records.

Create an execution manifest only after generating non-secret readiness records for the same protected-`main` candidate. Compute each file's lowercase SHA-256 digest, set the required decision, and run the manual **Public Operations Evidence Manifest** workflow.

The workflow verifies the exact checked-out candidate is an ancestor of protected `main`, rejects unsafe manifest paths and symlinks, recalculates every referenced file digest, checks every record candidate and decision, and emits a deterministic aggregate evidence digest retained for 90 days.

A valid result proves repository byte binding and decision consistency only. It does not prove live operations, staffing, legal compliance, deployment readiness, public registration, controlled beta authorization, payment collection, production billing, or general availability.
