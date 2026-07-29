# Public Operations Evidence Freshness

This control validates whether one exact public-operations evidence reconciliation record remains within an explicitly bounded review window for one exact protected-main candidate.

The validator binds the reconciliation file by repository-relative path and SHA-256, requires `NO-GO`, enforces RFC3339 UTC timestamps, limits the validity interval to 1–720 hours, rejects expired records, and requires separated owner and reviewer roles. It also rejects unknown keys, unsafe paths, symlinks, malformed digests, candidate drift, decision drift, and secret-like keys.

The committed example is intentionally structural only. It uses zero digests and an expired 2026 timestamp, so it cannot pass validation.

For a real record, first validate the reconciliation artifact independently. Record the lowercase SHA-256 of its exact bytes, use the same exact protected-main candidate and `NO-GO` decision, select a bounded review interval, assign distinct owner and reviewer roles, and run the manual **Public Operations Evidence Freshness** workflow.

A successful report states `VALID-NO-GO`. It proves only that the referenced repository evidence was consistent and within its declared review window at validation time. It does not deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
