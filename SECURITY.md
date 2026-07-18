# Security Policy

## Supported versions

Security fixes are applied to the current `main` branch and the latest active release candidate. Older development snapshots, forks, and unmaintained deployments are not supported.

## Reporting a vulnerability

Do not open a public issue, pull request, discussion, or comment for suspected vulnerabilities, exposed credentials, authentication bypasses, cross-user data access, prompt-injection paths involving private data, or infrastructure weaknesses.

Report security concerns privately to the repository owner or through GitHub private vulnerability reporting when enabled. Include only the information needed to reproduce and assess the problem:

- affected component and version or commit;
- reproduction steps using test data;
- expected and observed behavior;
- potential impact and affected trust boundary;
- logs or screenshots with secrets and personal data removed;
- suggested mitigation when known.

Do not access, alter, download, retain, or disclose data belonging to other users. Stop testing once the vulnerability is confirmed. Do not perform denial-of-service testing, social engineering, physical testing, or destructive actions without explicit written authorization.

## Response targets

- Critical: acknowledge within 1 business day and begin containment immediately.
- High: acknowledge within 2 business days.
- Medium or low: acknowledge within 5 business days.

These are targets rather than guarantees. Status updates and coordinated disclosure timing will be agreed upon after impact, exploitability, and remediation are understood.

## Release security gates

A staging or production release is blocked when any of the following remains unresolved:

- confirmed credential or secret exposure;
- authentication or authorization bypass;
- cross-user or cross-tenant data access;
- critical dependency or container vulnerability;
- high-severity vulnerability with a practical exploit path;
- missing software bill of materials for release images;
- failed static-analysis, dependency-audit, secret-scan, container-security, or deployment-validation workflow;
- unreviewed changes to security-sensitive authentication, authorization, memory, evidence, or AI-provider boundaries.

Exceptions require a documented owner, compensating controls, an expiration date, and explicit release approval.

## Secret and sensitive-data handling

- Never commit credentials, API keys, access tokens, private keys, kubeconfig files, Terraform state, database connection strings, or production data.
- Use protected GitHub environments and OIDC where possible.
- Keep local `.env` files outside version control and use documented example files with non-secret placeholders.
- Rotate a secret immediately when exposure is suspected; deleting the visible value is not sufficient.
- Treat workflow logs, screenshots, crash reports, database dumps, and uploaded artifacts as potentially sensitive.
- Do not paste secrets or exploit details into AI prompts, issue comments, pull requests, or acceptance records.

## AI and data-security expectations

Security-sensitive AI features must preserve authentication, owner or tenant isolation, provenance, and human oversight. Raw conversation content must not become validated knowledge automatically. Provider failures must degrade safely without exposing hidden prompts, credentials, private context, or another user's data.

## Financial application boundary

The LionsForge AI trading platform has been discontinued. Live trading, brokerage connectivity, order routing, autonomous portfolio execution, individualized financial advice, and regulated financial activity are outside the current product scope and require a separate product decision plus legal, security, privacy, and compliance review before implementation.