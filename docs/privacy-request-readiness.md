# Privacy Request Readiness

This versioned JSON record verifies that required privacy-request workflows have explicit repository metadata before any public-operations decision.

Required workflows are access, deletion, correction, portability, objection or restriction, and appeal. Each workflow must define a privacy role address, primary and backup owner roles, identity-verification method, fulfillment path, denial criteria, appeal route, acknowledgment and completion targets, a non-secret evidence reference, and verification status.

The validator rejects unknown keys, duplicate or missing workflows, placeholders, personal mailbox addresses, secret-like fields, invalid deadline ordering, unresolved identity checks, candidate mismatches, and GO decisions with any unverified workflow.

The committed example remains `NO-GO` and `NOT VERIFIED`. Its `.invalid` role addresses are non-routable examples and are not evidence of live channels, staffing, legal sufficiency, or jurisdictional compliance.

Run locally:

```bash
python scripts/validate_privacy_request_readiness.py docs/privacy-request-readiness.example.json --expected-candidate 0000000000000000000000000000000000000000
```

For an execution record, create a separate non-secret JSON file with an exact protected-`main` candidate, approved operational facts, legally reviewed deadlines, and immutable test references. Then use the manual **Privacy Request Readiness** workflow.

A valid record proves structure and candidate binding only. It does not provide legal advice, prove jurisdictional compliance, verify live channels or staffing, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
