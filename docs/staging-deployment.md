# Staging Deployment

The `Staging Deploy` GitHub Actions workflow deploys the backend to a persistent Kubernetes staging environment and runs authenticated smoke checks.

## Required GitHub environment

Create a repository environment named `staging`. Configure deployment approvals when manual authorization is required.

### Environment secrets

- `KUBE_CONFIG_STAGING`: base64-encoded kubeconfig with access limited to the staging cluster and namespace.
- `STAGING_DATABASE_URL`: staging database connection string.
- `STAGING_JWT_SECRET_KEY`: non-default signing secret for staging authentication.
- `STAGING_TEST_EMAIL`: email for a pre-provisioned staging acceptance account.
- `STAGING_TEST_SECRET`: credential for the staging acceptance account.

### Environment variable

- `STAGING_API_URL`: public HTTPS base URL for the deployed backend, without a trailing slash.

## Pre-deployment requirements

1. Provision the Kubernetes cluster, ingress controller, DNS, TLS certificate, and staging database.
2. Ensure the kubeconfig identity can manage resources only in `lionsforge-staging` where practical.
3. Create the staging test user through the normal registration flow before the first smoke run.
4. Confirm the GHCR image can be pulled by the cluster. Add an image-pull secret when the package is private.
5. Back up the staging database before migrations that are not backward compatible.

## Deployment execution

1. Open GitHub Actions.
2. Select `Staging Deploy`.
3. Choose `Run workflow`.
4. Supply an immutable image tag, normally the release-candidate commit SHA.
5. Approve the `staging` environment deployment when approval protection is enabled.

The workflow builds and pushes the backend image, applies staging manifests and secrets, waits for rollout completion, and executes `scripts/staging_smoke.py`.

## Acceptance gates

A successful workflow confirms:

- `/health`, `/ready`, and system readiness respond successfully.
- The staging account can authenticate.
- Dashboard, Mentor history, Research Projects, and Education APIs are reachable through authentication.

The broader manual acceptance journey remains defined in `docs/release-checklist.md` and must be completed before a Version 1.0 release decision.

## Rollback

1. Identify the last known-good image tag.
2. Run the workflow with that immutable tag, or set the deployment image directly.
3. Wait for Kubernetes rollout completion.
4. Re-run the staging smoke test.
5. Restore the database only when the failed release introduced an incompatible migration and the restore point has been validated.
