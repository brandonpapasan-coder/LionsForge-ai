# LionsForge AI Production Readiness Baseline

Status: release candidate baseline

## Approved product scope

LionsForge AI is a research assistant, evidence-validation platform, knowledge-management system, and elite education system.

The production scope includes authenticated research workflows, evidence review and validation, research projects and sessions, mentor-assisted learning, educational progress and assessment, governance and integrity artifacts, and supporting administrative and operational capabilities.

## Explicitly excluded scope

The production system must not provide or introduce:

- live trading or brokerage connectivity;
- order routing or trade execution;
- autonomous portfolio management;
- individualized financial advice;
- securities recommendations presented as personalized instructions.

Any future change that crosses these boundaries requires a separate product, legal, security, and architecture review before implementation.

## Required merge gates

Every production-bound change must pass the exact-head versions of:

1. Backend CI
2. Frontend CI
3. Security Gate
4. Deployment Validation

A pull request must not be merged when any required workflow is missing, pending, cancelled, skipped unexpectedly, or unsuccessful. The head SHA validated by the workflows must match the SHA supplied at merge time.

## API proxy resilience contract

Authenticated frontend API proxies must preserve these behaviors where applicable:

- missing session credentials return `401` without contacting the backend;
- unreadable request bodies return a controlled `400` response;
- backend connection failures return a stable `503` response without exposing internal URLs, tokens, stack traces, or transport details;
- unreadable upstream response bodies return a stable `503` response;
- upstream status codes and response bodies are preserved when they can be read safely;
- identifiers and path segments are URL encoded before forwarding;
- authenticated requests forward the bearer session token only to the configured backend;
- JSON requests and responses use the expected content type;
- backend calls use `cache: "no-store"`.

Focused regression tests must accompany changes to these guarantees.

## Authentication and session requirements

- Session cookies remain HTTP-only.
- Production cookies use the secure flag.
- Same-site behavior remains at least `lax` unless a reviewed integration requires a stricter setting.
- Authentication errors must not disclose backend implementation details.
- Successful login is the only login-proxy path permitted to create the application session cookie.

## Security baseline

Before release, confirm:

- no secrets, private keys, credentials, or production tokens are committed;
- dependency and security workflows are green;
- internal backend addresses and session values are not present in user-visible failures;
- authorization remains enforced on protected routes;
- security-sensitive configuration is supplied through deployment secrets or environment configuration;
- logging excludes request credentials and sensitive evidence content unless explicitly approved and redacted.

## Deployment readiness checklist

A release owner must confirm all items below against the candidate commit:

- required workflows passed on the exact release SHA;
- production environment variables and secrets are present;
- backend and frontend health checks are healthy;
- database migrations, when present, have a reviewed forward and rollback plan;
- application startup and authentication smoke tests pass;
- core research-project, research-session, mentor, assessment, and evidence-validation smoke tests pass;
- error responses do not expose internal service details;
- observability and alert destinations are configured;
- the rollback target is identified and deployable;
- release notes identify user-visible changes and known limitations.

## Rollback criteria

Rollback or disable the affected capability when any of the following occurs after deployment:

- authentication or authorization regression;
- evidence corruption, loss, or cross-user exposure;
- repeated backend failures without stable user-facing handling;
- critical workflow unavailable beyond the accepted operational threshold;
- security gate regression or confirmed secret exposure;
- a release violates the approved non-trading product boundary.

The rollback decision and resulting incident record must identify the release SHA, detection source, impact, mitigation, and follow-up owner.

## Operational ownership

Each production release requires named ownership for:

- release approval;
- deployment execution;
- backend and frontend health verification;
- security and incident response;
- rollback execution;
- post-release validation.

Ownership may be held by one person during early-stage operation, but the responsibilities must still be explicitly acknowledged.

## Release sign-off record

A production release is ready only when the release owner records:

- release commit SHA;
- required workflow run identifiers and successful conclusions;
- deployment environment;
- smoke-test result;
- rollback target;
- known limitations;
- final approval decision and date.

## Current readiness decision

The codebase may be classified as production-ready only after this baseline itself passes all required exact-head workflows and is merged. Production readiness describes the validated software baseline; it does not replace environment-specific deployment, legal, privacy, security, or operational approval.