# Staging Preflight Gate

Run `Staging Preflight` before Terraform planning, applying, or application deployment.

## What it verifies

- GitHub can assume the configured AWS plan role through OIDC.
- The Terraform state bucket exists and is reachable.
- State-bucket versioning, encryption, and public-access controls are readable.
- Plan and apply role ARNs are configured and different.
- Required AWS region, state bucket, API URL, and web URL variables are present.
- Staging API and web hostnames resolve through DNS.
- Both hostnames present valid HTTPS certificates.
- Backend health and readiness endpoints respond successfully.
- The public login page responds successfully.

## GitHub environment variables

Configure these variables in the `staging` environment:

- `AWS_REGION`
- `TF_STATE_BUCKET`
- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `AWS_TERRAFORM_APPLY_ROLE_ARN`
- `STAGING_API_URL`
- `STAGING_WEB_URL`

The apply role ARN is inspected only to confirm role separation. The preflight workflow assumes the plan role and does not modify AWS resources.

## Execution stages

Before infrastructure exists, run the workflow with `skip_endpoints=true`. This validates GitHub variables, OIDC authentication, and remote-state controls.

After ingress, DNS, TLS, and application deployment exist, run it with endpoint checks enabled. A successful full preflight is required before live acceptance.

## Failure handling

- Missing variable: configure the named GitHub environment variable.
- AWS identity failure: inspect the OIDC trust policy and repository environment name.
- State access failure: inspect the plan-role S3 policy and bucket ARN.
- DNS failure: correct the public records and wait for propagation.
- TLS failure: verify certificate issuance and ingress configuration.
- Health or readiness failure: inspect backend rollout, database connectivity, and migrations.
- Login-page failure: inspect frontend rollout and web ingress.

This workflow is non-destructive. It performs identity, metadata, DNS, TLS, and HTTP read checks only.
