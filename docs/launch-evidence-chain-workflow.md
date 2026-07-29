# Launch Evidence Chain Workflow

This manual workflow validates four completed, non-secret launch records against one exact protected-`main` candidate:

- production release record;
- public-operations activation record;
- controlled-beta acceptance record;
- general-availability decision record.

It validates the existing chain, generates the deterministic launch evidence-chain receipt, independently revalidates that receipt against the same source files, and retains the result for audit review.

The workflow proves record structure, integrity, and candidate binding only. It does not prove live evidence truth or freshness, provision infrastructure, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.

## Inputs

Provide one exact 40-character candidate SHA currently contained in protected `main` and repository-relative paths to the four completed records. Absolute paths and parent-directory traversal are rejected.

## Data handling

Do not include secrets, credentials, tester identities, private support content, request contents, uploaded evidence, private user data, or personal staff addresses. Use non-secret evidence identifiers and operational roles.
