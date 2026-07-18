# Staging Closeout Runbook

This is the operator sequence for closing Issue #29. Do not record credentials or secret values in this document, source control, issue comments, workflow output, or acceptance records.

## 1. Approve the staging target

Record the approved AWS account, AWS region, estimated monthly cost, approval owner, and intended immutable release commit SHA in `docs/staging-acceptance-record.md`.

Do not apply Terraform until account and cost approval are recorded.

## 2. Bootstrap remote state

From a trusted workstation authenticated to the approved AWS account:

```bash
cd infra/terraform/aws/bootstrap
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
terraform output -raw state_bucket_name
```

Copy `infra/terraform/aws/staging/backend.hcl.example` to a local `backend.hcl`, set the returned bucket name, and never commit that file.

## 3. Configure protected GitHub environments

Create or verify:

- `staging` for plan and application deployment
- `staging-apply` for protected infrastructure apply

Require an environment reviewer for `staging-apply` and use separate AWS OIDC roles for plan and apply permissions.

Required non-secret variables:

### `staging`

- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`
- `STAGING_API_URL`
- `STAGING_WEB_URL`

### `staging-apply`

- `AWS_TERRAFORM_APPLY_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`

Required `staging` secrets:

- `KUBE_CONFIG_STAGING`
- `STAGING_DATABASE_URL`
- `STAGING_JWT_SECRET_KEY`
- `STAGING_OPENAI_API_KEY`
- `STAGING_TEST_EMAIL`
- `STAGING_TEST_SECRET`

## 4. Plan and apply AWS staging

1. Dispatch `Terraform Staging Plan`.
2. Download and review the plan artifact.
3. Record the plan run ID, projected changes, cost impact, and approval.
4. Dispatch `Terraform Staging Apply` using the reviewed run ID and exact confirmation phrase `APPLY-STAGING`.
5. Retain the apply record artifact.

## 5. Verify the platform foundation

```bash
cd infra/terraform/aws/staging
terraform output -raw configure_kubectl_command
kubectl cluster-info
kubectl get nodes
```

Verify EKS nodes, private RDS connectivity, encryption, backups, deletion protection, final-snapshot controls, observability, and restore access.

## 6. Configure ingress, DNS, and TLS

Install the approved ingress controller and certificate manager. Configure valid HTTPS endpoints for:

- `api.staging.lionsforge.ai`
- `staging.lionsforge.ai`

Set `STAGING_API_URL` and `STAGING_WEB_URL` to those HTTPS origins.

## 7. Select the immutable release SHA

Choose an exact 40-character lowercase commit SHA from `main` whose Backend CI, Frontend CI, Security Gate, and Deployment Validation runs all succeeded. Record it in the acceptance record and use the same SHA for backend and frontend deployment.

## 8. Deploy backend and frontend

1. Dispatch `Staging Deploy` with the selected SHA as `image_tag`.
2. Confirm backend image build/push, Kubernetes apply, rollout, authenticated smoke checks, OpenAI provider health, and schema-valid Mentor response.
3. Dispatch `Staging Frontend Deploy` with the same SHA as `image_tag`.
4. Confirm frontend image build/push, rollout, and login-page smoke test.

## 9. Execute live acceptance

Complete `docs/release-checklist.md` and record evidence in `docs/staging-acceptance-record.md`, including:

- health and readiness
- Dashboard, Mentor, Research, and Education journeys
- retained compatibility checks in the release checklist
- OpenAI Mentor healthy and deterministic fallback behavior
- sign-out/sign-in persistence
- database backup and restore evidence
- rollback verification without an unsafe migration boundary
- critical and high-severity defect review

## 10. Record GO or NO-GO

A named owner records `GO` only when staging workflows pass on the recorded SHA, rollback is verified, acceptance evidence is complete, and no unresolved critical or high-severity defects remain. Otherwise record `NO-GO` with blockers and owners.

Close Issue #29 only after a signed `GO` decision.
