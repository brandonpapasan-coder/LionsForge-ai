# Security Release Gate

The `Security Gate` workflow is a required staging and production release control.

## Automated checks

### Static analysis

- Bandit scans Python application code.
- Semgrep scans backend and frontend source using its automatic ruleset.
- Reports are retained as workflow artifacts for 30 days.

### Dependency audit

- `pip-audit` evaluates Python dependencies from `backend/requirements.txt`.
- `npm audit` evaluates the frontend lockfile.
- High or critical findings fail the workflow.

### Secret detection

- Gitleaks scans the full available Git history.
- Confirmed credentials require immediate revocation and rotation, even when the commit is later removed.

### Container security

- Backend and frontend production images are built from the repository Dockerfiles.
- Trivy blocks unresolved high and critical vulnerabilities with available fixes.
- SPDX JSON software bills of materials are generated for both images.

## Triage process

1. Confirm the finding and affected component.
2. Determine whether the vulnerability is reachable in the LionsForge runtime.
3. Patch or upgrade the dependency, base image, configuration, or application code.
4. Re-run the complete security gate.
5. Record accepted risk only when remediation is not immediately possible.

## Exception record

A temporary exception must contain:

- finding identifier
- severity and affected component
- exploitability analysis
- compensating controls
- accountable owner
- expiration date
- planned remediation
- explicit release approver

Expired exceptions block release automatically through the release decision process, even when the workflow itself is green.

## Release evidence

For each release candidate retain:

- successful Security Gate run
- dependency audit reports
- static-analysis reports
- container scan reports
- backend and frontend SBOMs
- any approved, unexpired exception records

Security artifacts can contain package and filesystem metadata. Keep them within authorized release channels.
