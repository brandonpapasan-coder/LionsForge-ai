# Public Operations Witness-Checkpoint Ledger

This control records validated public-operations witness-ledger checkpoints in one deterministic append-only ledger for one exact protected-main candidate.

Each entry binds a checkpoint by repository-relative path, exact SHA-256, canonical checkpoint digest, contiguous sequence number, issue time, previous-entry digest, and deterministic entry digest. The validator preserves `NO-GO` and `VALID-NO-GO`, requires unique checkpoint paths and digests, requires strictly increasing checkpoint issue times, and rejects expired source checkpoints.

The validator rejects unknown keys, unsafe paths, symlinks, malformed or zero digests, duplicate paths or identities, source-byte drift, candidate or state drift, checkpoint-digest drift, sequence gaps, broken chain links, entry-digest drift, time regression, future issuance, expired checkpoints, malformed source JSON, and secret-like keys.

The committed example is structural only and cannot pass validation because its required digests are zero and its referenced checkpoint is expired.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It proves only internal chain and source consistency at validation time. It does not verify cryptographic signature authenticity, deploy software, enable registration, authorize beta, collect payments, enable production billing, or authorize general availability.
