# Support and Escalation Readiness

This versioned JSON record verifies that every required public channel has explicit repository metadata before any public-operations decision.

Required channels are general support, privacy requests, security reports, and abuse reports. Each channel must define a privacy-safe role address, primary and backup owner roles, monitored schedule, acknowledgment and resolution targets, critical escalation timing, escalation ownership, after-hours coverage, a non-secret test-evidence reference, and verification status.

The validator rejects unknown keys, duplicate or missing channels, placeholders, personal mailbox addresses, secret-like fields, invalid response-target ordering, unresolved backup coverage, candidate mismatches, and GO decisions with any unverified channel.

The committed example remains `NO-GO` and `NOT VERIFIED`. Its `.invalid` role addresses are non-routable examples and are not evidence of live channels or staffing.

Run locally:

```bash
python scripts/validate_support_escalation_readiness.py docs/support-escalation-readiness.example.json --expected-candidate 0000000000000000000000000000000000000000
```

For an execution record, create a separate non-secret JSON file with an exact protected-`main` candidate, approved role addresses and operational facts, and immutable test references. Then use the manual **Support Escalation Readiness** workflow.

A valid record proves structure and candidate binding only. It does not prove live channel availability, staffing, legal approval, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
