# LionsForge AI Release Checklist

A release candidate is eligible for staging only when every required gate below is green.

## Release candidate

- Record the exact 40-character `main` commit SHA being evaluated.
- Confirm Backend CI, Frontend CI, Security Gate, and Deployment Validation passed on a `push` event for `main` at that exact SHA.
- Treat pull-request runs, manual runs, scheduled runs, branch runs, missing status contexts, or unverifiable run evidence as insufficient.
- Use the same immutable SHA as both the `Staging Deploy` and `Staging Frontend Deploy` workflow `image_tag`.
- Do not substitute a branch name, moving tag, locally built image, or an unverified merge SHA.

## GitHub `staging` environment

Required secrets:

- `KUBE_CONFIG_STAGING`
- `STAGING_DATABASE_URL`
- `STAGING_JWT_SECRET_KEY`
- `STAGING_OPENAI_API_KEY`
- `STAGING_TEST_EMAIL`
- `STAGING_TEST_SECRET`

Required variables:

- `STAGING_API_URL` using a non-empty HTTPS URL
- `STAGING_WEB_URL` using a non-empty HTTPS URL

Secret values must never be committed, echoed, copied into issue comments, or stored in acceptance artifacts.

## Automated gates

- Backend CI passes the full test suite on a `push` event for `main` at the exact release SHA.
- Frontend CI passes tests, type checking, and the production build on a `push` event for `main` at the exact release SHA.
- Deployment Validation applies all Alembic migrations from a clean database on a `push` event for `main` at the exact release SHA.
- Security Gate contains no unresolved critical findings on a `push` event for `main` at the exact release SHA.
- `Staging Deploy` completes backend image build, push, digest resolution, Kubernetes apply, rollout, running-image verification, and authenticated smoke validation.
- `Staging Frontend Deploy` completes frontend image build, push, digest resolution, Kubernetes apply, rollout, running-image verification, and login-page smoke validation.
- Staging smoke validation confirms:
  - health and readiness endpoints respond successfully
  - authenticated Dashboard, Mentor, Research, and Education APIs respond successfully
  - OpenAI Mentor provider is enabled and configured or healthy
  - a Mentor request returns the complete schema-valid response contract

## Security gates

- No secrets are committed to the repository or exposed in workflow output.
- Authentication is required for Dashboard, Mentor, Research, and Education APIs.
- Cross-user access tests pass for persisted user data.
- Staging uses a non-default JWT secret and HTTPS-only session cookies.
- Dependency and container vulnerability scans contain no unresolved critical findings.

## Operational gates

- Kubernetes namespace, ingress, DNS, TLS, PostgreSQL, and GHCR image-pull access are operational.
- Database backup and restore procedure is documented and tested.
- Health checks are configured for backend, frontend, and database services.
- Application errors and latency are observable in staging.
- Rollback identifies the previous backend and frontend image digests and the database migration boundary.
- A named owner is assigned for every acceptance defect.

## Staging acceptance journey

1. Register or use the designated staging acceptance user.
2. Sign in and load the Executive Dashboard.
3. Create a research project and save notebook content.
4. Create and reopen a research session.
5. Open the AI Mentor from the Research Workspace.
6. Verify the Mentor receives resolved project, session, and notebook context.
7. Verify the Mentor returns a complete evidence-first response without unsupported live-verification claims.
8. Reopen the saved Mentor conversation and continue it.
9. Open the Education Hub, start a lesson, and complete it.
10. Open the market-learning command-center panels and confirm their educational disclaimers are visible.
11. Sign out and sign back in.
12. Verify research, mentor, education, and market-learning state persists.
13. Exercise the documented rollback procedure without crossing an unsafe migration boundary.
14. Record both deployment workflow runs, both immutable image digests, and both running-image verifications in `docs/staging-acceptance-record.md`.
15. Run `Staging Acceptance Validate` against the completed record and exact release SHA.

## Release decision

- **GO:** exact-SHA `push`/`main` gates are verified, both staging deploy workflows pass, all automated and operational gates pass, the acceptance journey succeeds, rollback is verified, the completed record passes validation, and no unresolved critical or high-severity defects remain.
- **NO-GO:** required exact-SHA `push`/`main` evidence is missing or unverifiable, any required gate fails, provider configuration is missing, data persistence is unreliable, authentication isolation fails, critical safety language is absent, image provenance is incomplete, or rollback cannot be executed safely.
