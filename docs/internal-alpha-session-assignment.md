# Internal Alpha Session Assignment

This control validates privacy-safe session assignments for approved internal-alpha testers on one exact protected-main candidate.

Each session binds a pseudonymous tester ID to an immutable release-candidate identifier, least-privilege purpose (`research`, `validation`, or `usability`), pseudonymous approver reference, isolated internal-alpha environment, and bounded issue/start/end times. Sessions may last no more than 12 hours.

The validator rejects unknown keys, personal or secret-like fields, malformed identifiers, duplicate session IDs, duplicate tester/release assignments, overlapping sessions for one tester, privileged purposes, public or production environments, candidate drift, future issuance, expired sessions, sessions beginning before issuance, excessive duration, and authorization escalation.

The committed example is structural only and cannot pass current validation because its candidate is a placeholder and its session is expired.

A successful result preserves `INTERNAL-ALPHA-ONLY`. It validates assignment records only; it does not create accounts or credentials, grant network access, enable public registration, authorize external beta, deploy software, collect payments, enable production billing, or authorize general availability.
