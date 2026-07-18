# LionsForge AI Release Checklist

A release candidate is eligible for staging only when every required gate below is green.

## Release candidate

- Record the exact 40-character `main` commit SHA being evaluated.
- Confirm Backend CI, Frontend CI, Security Gate, and Deployment Validation successful `push` runs exist for that exact SHA on `main`.
- Use the same immutable SHA as the `image_tag` for both `Staging Deploy` and `Staging Frontend Deploy`.
- Do not substitute a branch name, moving tag, manual workflow result, or locally built image.

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

- Backend CI passes the full test suite.
- Frontend CI passes tests, type checking, and the production build.
- Deployment Validation applies all Alembic migrations from a clean database.
- Security Gate contains no unresolved critical findings.
- `Staging Deploy` builds and pushes the backend image, resolves its immutable `sha256` digest, deploys by digest, verifies every running backend image ID, completes Kubernetes rollout, and passes authenticated smoke validation.
- `Staging Frontend Deploy` builds and pushes the frontend image, resolves its immutable `sha256` digest, deploys by digest, verifies every running frontend image ID, completes Kubernetes rollout, and passes the login-page smoke check.
- Staging smoke validation confirms:
  - health and readiness endpoints respond successfully
  - authenticated Dashboard, Mentor, Research, and Education APIs respond successfully
  - OpenAI Mentor provider is enabled and configured or healthy
  - a Mentor request returns the complete schema-valid response contract
- `Staging Acceptance Validate` confirms exact-SHA release-gate evidence and internal acceptance-record consistency.

## Image provenance gates

- Record the backend staging workflow run and registry digest.
- Record the frontend staging workflow run and registry digest.
- Confirm the running backend image digest matches the recorded backend digest.
- Confirm the running frontend image digest matches the recorded frontend digest.
- Confirm both deployments were dispatched using the same release candidate SHA.
- Do not approve GO using image tags alone.

## Security gates

- No secrets are committed to the repository or exposed in workflow output.
- Authentication is required for Dashboard, Mentor, Research, and Education APIs.
- Cross-user access tests pass for persisted user data.
- Staging uses a non-default JWT secret and HTTPS-only session cookies.
- Dependency and container vulnerability scans contain no unresolved critical findings.

## Operational gates

- Kubernetes namespace, ingress, API and web DNS, TLS, PostgreSQL, and GHCR image-pull access are operational.
- Database backup and restore procedure is documented and tested.
- Health checks are configured for backend, frontend, and database services.
- Application errors and latency are observable in staging.
- Rollback identifies the previous backend and frontend images and the database migration boundary.
- A named owner is assigned for every acceptance defect.

## Staging acceptance journey

1. Register or use the designated staging acceptance user.
2. Sign in through the deployed frontend and load the Executive Dashboard.
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
14. Forward-deploy the same accepted backend and frontend digests after the rollback test.
15. Record results in `docs/staging-acceptance-record.md`.
16. Run `Staging Acceptance Validate` against the completed record and exact release SHA.

## Release decision

- **GO:** all automated, provenance, security, and operational gates pass; the acceptance journey succeeds; rollback and forward redeploy are verified; both running image digests match the record; and no unresolved critical or high-severity defects remain.
- **NO-GO:** any required gate fails, either image provenance check is incomplete, provider configuration is missing, data persistence is unreliable, authentication isolation fails, critical safety language is absent, or rollback cannot be executed safely.
