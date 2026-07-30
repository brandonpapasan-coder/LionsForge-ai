# Internal Alpha Feedback

This control validates privacy-safe feedback records from isolated internal-alpha sessions for one exact protected-main candidate.

Each record binds a pseudonymous tester and session ID to an immutable release candidate, controlled category, severity, reproducibility state, component code, bounded reason codes, and an observation time inside the referenced session window. Free-form text, attachments, personal data, and secret-like fields are intentionally excluded.

The validator rejects unknown or sensitive fields, malformed identifiers, duplicate feedback IDs, public or production environments, candidate drift, authorization escalation, invalid category/severity combinations, invalid reproducibility, future observations, observations outside session windows, duplicate reason codes, and oversized manifests.

The committed example is structural only and cannot pass current validation because its candidate is a placeholder and its observation is historical.

A successful result preserves `INTERNAL-ALPHA-ONLY`. It validates feedback records only; it does not create accounts or credentials, expose feedback publicly, enable external beta, deploy software, collect payments, enable production billing, or authorize general availability.
