# LionsForge AI Deployment Guide

## Deployment stages

### Staging

Staging is the first always-on environment. Every merge into `main` should be eligible for staging deployment after CI passes.

Expected checks before staging deployment:

- Backend CI green
- Deployment Validation green
- Docker image built successfully
- Kubernetes manifests render successfully
- Required secrets exist in the staging cluster

### Production

Production deployments should require manual approval until the platform has operational maturity.

Expected checks before production deployment:

- Staging deployment healthy
- Smoke tests pass against staging
- Database migration reviewed
- Rollback image tag identified
- Monitoring dashboards healthy

## Required runtime secrets

The backend expects these secrets at runtime:

```text
DATABASE_URL
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
MARKET_DATA_API_KEY
NEWS_API_KEY
```

Use a cloud secret manager or sealed secrets. Do not commit real secret values.

## Kubernetes layout

```text
infra/k8s/backend
infra/k8s/overlays/staging
infra/k8s/overlays/production
```

Render manifests locally:

```bash
kubectl kustomize infra/k8s/overlays/staging
kubectl kustomize infra/k8s/overlays/production
```

## Rollback approach

1. Keep the previous backend image tag available.
2. Deploy the previous tag to the target environment.
3. Confirm `/health` and `/ready` are passing.
4. Review logs and database compatibility.
5. Open a follow-up issue for the failed release.

## Migration approach

Migrations should be automated with Alembic before backend pods roll forward. For destructive migrations, require manual approval and a backup checkpoint.
