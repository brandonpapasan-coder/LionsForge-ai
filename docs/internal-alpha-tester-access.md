# Internal Alpha Tester Access

This control validates a privacy-safe manifest of approved internal-alpha testers for one exact protected-main candidate.

Each tester is represented only by a pseudonymous tester ID and approver reference. Access must be approved, assigned to one least-privilege role (`reader`, `researcher`, or `validator`), bound to the isolated internal-alpha environment, issued no more than five minutes in the future, unexpired, and limited to at most 30 days.

The validator rejects unknown keys, personal or secret-like fields, malformed identifiers, duplicate testers, unapproved status, privileged roles, public or production environments, candidate drift, future issuance, expired access, and excessive duration. The output is deterministic and includes only pseudonymous tester IDs and non-secret digests.

The committed example is structural only and cannot pass current validation because its candidate is a placeholder and its access period is expired.

A successful result grants only `INTERNAL-ALPHA-ONLY` authorization. It does not create accounts, issue credentials, enable public registration, authorize external beta, deploy software, collect payments, enable production billing, or authorize general availability.
