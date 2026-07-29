# Public Data Inventory

The public data inventory is a versioned, repository-safe JSON record used to verify that every required public-operations data class has explicit handling metadata before any public launch decision.

Required coverage includes account data, uploaded evidence, generated content, education and mastery history, telemetry, authentication and security logs, support and privacy records, provider-bound request data, and backups.

Each class must identify its purpose, storage locations, access roles, retention rule, deletion path, backup handling, subprocessor status, personal-data classification, secret classification, and verification status. Duplicate identifiers, unknown keys, placeholders, secret-like fields, missing required classes, unresolved metadata, and candidate mismatches fail closed.

The committed example remains `NO-GO` and uses `NOT VERIFIED` statuses. It is a structural example only and must not be treated as evidence that live systems, legal approvals, subprocessors, support channels, or privacy operations are ready.

## Validation

Run:

```bash
python scripts/validate_public_data_inventory.py docs/public-data-inventory.example.json --expected-candidate 0000000000000000000000000000000000000000
```

For an execution record, copy the example to a new non-secret JSON file, replace the candidate with a freshly selected exact protected-`main` SHA, replace example metadata with approved operational facts and references, and run the manual **Public Data Inventory** workflow.

A valid inventory proves record completeness and candidate binding only. It does not provide legal approval, verify live systems, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
