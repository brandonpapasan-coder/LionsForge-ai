# Production Evidence Index

Use this workflow only after staging issue #29 has a verified accepted result and a fresh production candidate has been selected from protected `main`.

## Purpose

The index binds one production candidate and one accepted staging candidate to the complete production evidence package. It summarizes supplied evidence only; it does not provision production, deploy workloads, perform live verification, enable public registration, authorize controlled beta, or approve general availability.

## Required operator inputs

- `candidate_sha`: exact lowercase 40-character production candidate SHA contained in protected `main`.
- `staging_candidate_sha`: exact accepted staging candidate SHA for the same release lineage.
- `selection_rationale`: concise explanation of candidate and lineage selection.
- `entries_json`: JSON array containing exactly the required categories defined by `scripts/manage_production_evidence_index.py`.

Each entry must contain:

- category
- production candidate SHA
- accepted staging candidate SHA
- positive artifact ID
- HTTPS artifact URL
- `sha256:` artifact digest
- positive workflow run ID
- verification boolean
- `passed`, `failed`, or `incomplete` status
- `GO`, `NO-GO`, or `NOT-APPLICABLE` decision
- UTC observation timestamp ending in `Z`
- non-empty summary without credentials, secrets, private content, or request data

## Decision contract

`READY` requires every mandatory entry to be structurally valid, verified, passed, bound to both exact candidates, and internally consistent. The accepted staging evidence index and final production release record must both record `GO`.

Structurally valid failed, incomplete, unverified, candidate-mismatched, lineage-mismatched, or `NO-GO` evidence produces a receipted `NOT-READY` index. Malformed, duplicate, missing, extra, sensitive, or tampered evidence is rejected.

## Artifact handling

The workflow uploads `production-evidence-index.json` before final readiness enforcement and retains it for 90 days. Record the workflow run ID, artifact ID, artifact URL, and artifact digest in the production execution tracker without copying sensitive evidence into issues.

## External gates

A repository index marked `READY` is evidence organization only. Production infrastructure, live verification, public operations, legal/privacy/support readiness, controlled beta, and general availability require independent completion of issues #401, #402, #403, and #400.
