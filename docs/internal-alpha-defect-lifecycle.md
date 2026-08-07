# Internal Alpha Defect Lifecycle

This control validates privacy-safe defect lifecycle records derived from isolated internal-alpha feedback for one exact protected-main candidate.

Each record binds a defect to pseudonymous feedback, tester, session, owner, and release-candidate identifiers; controlled severity and regression states; bounded reason codes; deterministic lifecycle states; and ordered creation, update, and verification timestamps.

The validator rejects unknown, personal, secret-like, or free-form fields; malformed identifiers; duplicate defect or feedback IDs; public or production environments; candidate drift; authorization escalation; lifecycle regression; unverified closure; unapproved severity downgrades; invalid timestamp ordering; future timestamps; and oversized manifests.

The committed example is structural only and cannot pass current validation because its candidate is a placeholder and its timestamps are historical.

A successful result preserves `INTERNAL-ALPHA-ONLY`. It validates and summarizes defect records only; it does not expose defects publicly, create accounts or credentials, enable external beta, deploy software, collect payments, enable production billing, authorize general availability, or introduce trading functionality.
