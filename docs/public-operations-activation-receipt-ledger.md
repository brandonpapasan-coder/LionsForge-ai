# Public Operations Activation Receipt Ledger

This ledger provides an append-only, cryptographically chained history of public-operations activation receipts. Each entry binds an exact receipt file, candidate SHA, decision, activation mode, authorization digest, issuance time, and the prior entry digest.

The validator rejects unknown keys, unsafe paths, symlinks, malformed digests, duplicate receipt identifiers, non-contiguous sequence numbers, non-monotonic timestamps, broken previous-entry links, receipt-byte drift, metadata drift, entry-digest drift, ledger-digest drift, and secret-like keys.

The committed example is an empty, non-authorizing ledger. It contains no activation receipts and cannot authorize public operations.

For each new receipt, validate the receipt first, append exactly one new entry with the next sequence number and previous entry digest, compute its deterministic entry digest, and recompute the ledger digest over the ordered entry-digest list. Never edit or delete prior entries.

A valid ledger proves repository receipt-history integrity only. It does not activate public operations, deploy software, enable registration, authorize controlled beta, collect payments, enable production billing, or authorize general availability.
