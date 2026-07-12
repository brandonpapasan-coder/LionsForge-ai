# Security Policy

## Supported release

Security fixes are applied to the current `main` branch and the latest active release candidate. Older development snapshots are not supported.

## Reporting a vulnerability

Do not open a public issue for suspected vulnerabilities, exposed credentials, authentication bypasses, cross-user data access, or infrastructure weaknesses.

Report security concerns privately to the repository owner or through GitHub private vulnerability reporting when enabled. Include:

- affected component and version or commit
- reproduction steps
- expected and observed behavior
- potential impact
- logs or screenshots with secrets removed
- suggested mitigation when known

Do not access, alter, or retain data belonging to other users. Stop testing once the vulnerability is confirmed.

## Response targets

- Critical: acknowledge within 1 business day and begin containment immediately.
- High: acknowledge within 2 business days.
- Medium or low: acknowledge within 5 business days.

Timelines are targets rather than guarantees. Coordinated disclosure timing will be agreed upon after impact and remediation are understood.

## Release security gates

A staging or production release is blocked when any of the following remains unresolved:

- confirmed credential or secret exposure
- authentication or authorization bypass
- cross-user data access
- critical dependency or container vulnerability
- high-severity vulnerability with a practical exploit path
- missing software bill of materials for release images
- failed static-analysis, dependency-audit, secret-scan, or container-security workflow

Exceptions require a documented owner, compensating controls, an expiration date, and explicit release approval.

## Secret handling

- Never commit credentials, API keys, kubeconfig files, Terraform state, or database connection strings.
- Use protected GitHub environments and OIDC where possible.
- Rotate a secret immediately when exposure is suspected.
- Treat workflow logs and uploaded artifacts as potentially sensitive and redact them before sharing.

## Financial application note

The LionsForge trading platform has been discontinued. Any future feature involving live trading, portfolio execution, or regulated financial activity requires separate legal, security, and compliance review before implementation or release.
