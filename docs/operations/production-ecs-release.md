# OnyxMane AWS ECS Production Release

The active production architecture is AWS ECS + ECR + ALB. Kubernetes/GHCR production deployment workflows remain only as legacy history and must not be used for the live OnyxMane production environment.

## Protected GitHub environment

Use the `production` GitHub environment. Deployment workflows require non-secret environment variables matching the live AWS resources:

- `AWS_REGION`
- `AWS_PRODUCTION_DEPLOY_ROLE_ARN`
- `ECR_BACKEND_REPOSITORY`
- `ECR_FRONTEND_REPOSITORY`
- `ECS_PRODUCTION_CLUSTER`
- `ECS_PRODUCTION_BACKEND_SERVICE`
- `ECS_PRODUCTION_FRONTEND_SERVICE`
- `ECS_BACKEND_CONTAINER_NAME`
- `ECS_FRONTEND_CONTAINER_NAME`
- `PRODUCTION_WEB_URL`

Runtime application secrets remain in AWS Secrets Manager or SSM and are preserved through the current ECS task definition. Do not copy runtime secret values into GitHub workflow inputs, repository files, issue comments, or deployment summaries.

## Backend release

Dispatch `Production ECS Backend Deploy` with one exact 40-character lowercase commit SHA contained in protected `main`. Supply a prior immutable SHA as `rollback_sha` when available.

The workflow:

1. verifies the selected release and rollback commits belong to `main`;
2. authenticates to AWS using GitHub OIDC;
3. builds and pushes the backend image to ECR under the immutable release SHA tag;
4. resolves the image to its ECR `sha256` digest;
5. reads the currently running ECS task definition;
6. replaces only the backend container image;
7. deploys a new task-definition revision and waits for service stability; and
8. records release provenance without exposing runtime secrets.

## Frontend release

Dispatch `Production ECS Frontend Deploy` using the same selected release SHA as the backend release unless an explicitly reviewed split release is required.

The frontend workflow performs equivalent immutable ECR and ECS deployment controls, then verifies every running frontend task reports the expected image digest and smoke-tests `PRODUCTION_WEB_URL/login`.

## Required release evidence

For release acceptance retain:

- selected `main` release SHA and rationale;
- required CI/security/deployment-validation workflow results;
- backend and frontend ECR digests;
- previous and resulting ECS task-definition revisions;
- ECS desired/running/pending counts after stability;
- running frontend digest verification;
- ALB target-group health;
- HTTPS API/web and authenticated application smoke results;
- rollback and restore evidence; and
- operational monitoring/cost evidence required by issue #401.

A successful deployment does not by itself authorize controlled beta or general availability.
