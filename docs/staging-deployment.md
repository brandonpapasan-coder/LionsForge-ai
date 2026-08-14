# Staging Deployment

OnyxMane staging now follows the same AWS ECS + Amazon ECR deployment model proven in production. Kubernetes-specific staging deployment remains legacy and must not be used for new staging releases unless that architecture is explicitly re-approved.

## Required GitHub environment

Create or maintain a protected repository environment named `staging`. Use deployment approvals where manual authorization is required.

### Environment secrets

Application credentials remain environment secrets and must never be committed or printed:

- `STAGING_DATABASE_URL`
- `STAGING_JWT_SECRET_KEY`
- `STAGING_OPENAI_API_KEY`
- `STAGING_TEST_EMAIL`
- `STAGING_TEST_SECRET`

### Environment variables

AWS/ECS deployment configuration is stored as environment variables:

- `AWS_REGION`
- `AWS_STAGING_DEPLOY_ROLE_ARN`
- `ECR_BACKEND_REPOSITORY`
- `ECR_FRONTEND_REPOSITORY`
- `ECS_STAGING_CLUSTER`
- `ECS_STAGING_BACKEND_SERVICE`
- `ECS_STAGING_FRONTEND_SERVICE`
- `ECS_BACKEND_CONTAINER_NAME`
- `ECS_FRONTEND_CONTAINER_NAME`
- `STAGING_API_URL`
- `STAGING_WEB_URL`

The AWS deploy role must use GitHub OIDC and least privilege for the required ECR and ECS operations.

## Pre-deployment requirements

1. Provision an isolated ECS staging cluster or an explicitly isolated staging service set.
2. Provision backend and frontend ECS services with task definitions, target groups, load-balancer routing, DNS, and valid TLS.
3. Provision the staging PostgreSQL database and migration path.
4. Configure the `staging` GitHub environment variables and secrets above.
5. Confirm the AWS deploy role can authenticate through GitHub OIDC and has only the required ECR/ECS permissions.
6. Create the staging acceptance user through the normal application flow before the first authenticated smoke run.
7. Confirm backup, restore, observability, incident-response, and rollback ownership before acceptance.

## Deployment execution

Use one fresh exact 40-character commit SHA contained in protected `main` for the complete staging candidate.

1. Run `Staging Preflight` with the selected immutable SHA and endpoint checks enabled.
2. Run `Staging ECS Backend Deploy` using the same SHA as `release_sha`.
3. Run `Staging ECS Frontend Deploy` using the same SHA as `release_sha`.
4. Verify both ECR images resolve to immutable `sha256` digests.
5. Verify both ECS services become stable with desired count equal to running count and zero pending tasks.
6. Confirm ALB target health before application acceptance.
7. Execute authenticated staging smoke and the broader release checklist.

The deployment workflows preserve the existing ECS task-definition configuration and secret bindings while replacing only the selected container image.

## Acceptance gates

A staging release cannot be marked accepted until all mandatory live checks pass, including:

- backend and frontend services are ACTIVE and stable;
- running containers use the intended immutable release image;
- target groups report healthy registered targets;
- public staging endpoints use HTTPS;
- `/health`, `/ready`, and system readiness succeed where exposed;
- the staging acceptance account can authenticate;
- Mentor, Research Projects, evidence/research workflows, Education, and other required protected journeys succeed;
- backup/restore, observability, incident-response, and rollback exercises have verified evidence.

The broader acceptance journey remains defined in `docs/release-checklist.md` and `docs/staging-closeout-runbook.md`.

## Rollback

1. Record the previous immutable commit SHA before each staging deployment.
2. Prefer redeploying the last known-good SHA through the ECS workflow so ECR provenance remains traceable.
3. If immediate service recovery is required, restore the previous ECS task definition, then verify service stability and target health.
4. Re-run HTTPS and authenticated smoke checks.
5. Restore the database only when an incompatible migration requires it and the restore point has already been validated.

## Legacy Kubernetes path

`.github/workflows/staging-frontend-deploy.yml`, Kubernetes overlays, and `KUBE_CONFIG_STAGING` describe the older staging model. They are retained temporarily for audit/history, but the ECS workflows are the active staging release path. Remove or archive the legacy path only after the ECS staging environment has completed acceptance and no rollback dependency remains.
