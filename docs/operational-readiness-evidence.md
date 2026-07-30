# Operational Readiness Evidence Aggregator

This control combines existing non-secret validation reports for one exact protected-main candidate into one deterministic readiness snapshot.

Each manifest entry binds one evidence type to a safe repository-relative report path, exact file SHA-256, canonical report digest, issue time, and expiration time. Every source report must bind the same candidate, expose exactly one `VALID-NO-GO` state field, and preserve `authorization: NONE`.

The validator rejects unknown manifest or entry keys, malformed or zero digests, secret-like keys, unsafe paths, symlinks, missing files, malformed JSON, byte drift, digest drift, candidate drift, state drift, authorization escalation, issue-time drift, expiration drift, future issuance, expired evidence, and duplicate evidence identities. Evidence is sorted by type before the aggregate digest is calculated, making the resulting snapshot deterministic regardless of manifest entry order.

The committed example is structural only and cannot pass validation because its digests are zero, its candidate is a placeholder, its referenced report is not supplied, and its evidence is expired.

A successful result is `VALID-NO-GO` with `authorization: NONE`. It is an internal consistency statement only. It does not verify live infrastructure, cryptographic signature authenticity, external approvals, deployment readiness, public registration, beta authorization, payments, production billing, or general availability.
