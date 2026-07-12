# Terraform Remote State Bootstrap

This stack creates the S3 bucket used by the LionsForge AWS staging Terraform backend.

## Safety properties

- private S3 bucket
- public access blocked
- server-side encryption enabled
- versioning enabled
- noncurrent versions retained for 90 days
- force deletion disabled by default

## Bootstrap sequence

Run this stack once using local state:

```bash
cd infra/terraform/aws/bootstrap
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
terraform output -raw state_bucket_name
```

Copy `infra/terraform/aws/staging/backend.hcl.example` to `backend.hcl` and replace the bucket placeholder with the output value.

Initialize the staging stack:

```bash
cd ../staging
terraform init -backend-config=backend.hcl
terraform plan
```

Do not commit `backend.hcl`, local state, plan files, credentials, or generated secrets.

## GitHub plan workflow

The `Terraform Staging Plan` workflow is plan-only and cannot apply infrastructure. Configure these variables in the GitHub `staging` environment:

- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`

The AWS role should trust GitHub OIDC for this repository and have only the permissions needed to read state, acquire the S3 lockfile, and calculate the staging plan. Keep apply permissions in a separate, manually controlled role.
