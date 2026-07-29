# Incident Communication Readiness

This versioned JSON record verifies that required incident classes have explicit communication metadata before any public-operations decision.

Required classes are availability, security, privacy, data integrity, and provider dependency. Each class must define primary and backup command roles, severity threshold, initial and recurring update timing, user-notice criteria, restoration messaging, post-incident review timing, a non-secret evidence reference, and verification status.

The validator rejects unknown keys, duplicate or missing classes, placeholders, secret-like fields, unresolved ownership, invalid timing order, candidate mismatches, and GO decisions with any unverified incident class.

The committed example remains `NO-GO` and `NOT VERIFIED`. It is not evidence of live status infrastructure, staffing, exercises, legal notification compliance, or production readiness.

Run locally:

```bash
python scripts/validate_incident_communication_readiness.py docs/incident-communication-readiness.example.json --expected-candidate 0000000000000000000000000000000000000000
```

For an execution record, create a separate non-secret JSON file with an exact protected-`main` candidate, approved operational facts, legally reviewed notice criteria, and immutable exercise references. Then use the manual **Incident Communication Readiness** workflow.

A valid record proves structure and candidate binding only. It does not prove live status infrastructure, staffing, legal notification compliance, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
