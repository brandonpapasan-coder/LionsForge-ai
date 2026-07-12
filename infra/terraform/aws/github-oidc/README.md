# GitHub OIDC Terraform Roles

This stack creates two repository-scoped AWS IAM roles:

- `lionsforge-terraform-staging-plan` trusts only the GitHub `staging` environment.
- `lionsforge-terraform-staging-apply` trusts only the GitHub `staging-apply` environment.

Both roles receive access only to the staging Terraform state path. Resource permissions required to inspect or modify AWS infrastructure must be attached separately after IAM review.

## Required GitHub environments

### `staging`

Configure:

- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`

### `staging-apply`

Configure required reviewers and prevent self-approval where supported. Configure:

- `AWS_TERRAFORM_APPLY_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`

## Apply controls

The apply workflow:

- is manual only
- requires the exact confirmation phrase `APPLY-STAGING`
- requires a prior plan workflow run ID
- downloads the reviewed plan artifact
- verifies the rendered plan before apply
- uses a dedicated apply role
- serializes applies with GitHub Actions concurrency
- stores an apply record for 30 days

Do not grant the plan role write access to AWS platform resources. Attach only read permissions needed to calculate plans. Grant the apply role only the resource actions required by the reviewed staging stack, preferably with a permissions boundary and AWS Organizations service-control policies.
