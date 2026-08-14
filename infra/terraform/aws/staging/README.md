# AWS ECS Staging Infrastructure

This Terraform stack provisions the persistent OnyxMane staging foundation on AWS using the same ECS + ECR + ALB architecture validated in production.

It creates:

- a VPC with public, private, and database subnets across two availability zones
- an ECS Fargate cluster with isolated backend and frontend services
- immutable ECR repositories for backend and frontend images
- an Application Load Balancer with backend and frontend target groups
- optional HTTPS using an ACM certificate, with HTTP-to-HTTPS redirect when configured
- CloudWatch log groups and ECS task execution/task roles
- a private PostgreSQL 16 RDS instance reachable only from ECS tasks
- encrypted database storage, seven-day backups, deletion protection, and a required final snapshot

## Cost warning

Applying this stack creates billable AWS resources, including NAT Gateway, ECS/Fargate tasks, ALB, RDS, CloudWatch logs, and data transfer. Review estimated monthly cost before applying.

## Prerequisites

- Terraform 1.8 or later
- a secure remote Terraform state backend
- GitHub OIDC plan and apply roles for the protected staging environments
- initial backend and frontend ECR image URIs that can start successfully
- an ACM certificate ARN before acceptance testing
- backend application secrets stored in AWS Secrets Manager or SSM Parameter Store

Never put secret values in `.tfvars`, source control, workflow output, issue comments, or Terraform plan text. `backend_secrets` accepts secret or parameter ARNs only; ECS resolves their values at runtime.

## Protected GitHub execution

The recommended provisioning path is GitHub Actions, not an operator workstation.

Configure the `staging` environment variables:

- `AWS_REGION`
- `TF_STATE_BUCKET`
- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `STAGING_BOOTSTRAP_BACKEND_IMAGE`
- `STAGING_BOOTSTRAP_FRONTEND_IMAGE`
- `STAGING_ACM_CERTIFICATE_ARN`

Configure the `staging` environment secret:

- `STAGING_BACKEND_SECRET_ARNS_JSON`

`STAGING_BACKEND_SECRET_ARNS_JSON` must be a JSON object containing at least `DATABASE_URL`, `JWT_SECRET_KEY`, and `OPENAI_API_KEY`, with each value set to an AWS Secrets Manager or SSM Parameter Store ARN. It must contain no secret values.

The bootstrap backend and frontend image variables must use immutable ECR image tags that are exact 40-character commit SHAs. They may point to known-good images already present in the account for the first infrastructure creation. After ECS services exist, normal staging releases are performed by the dedicated ECS deployment workflows.

Configure the protected `staging-apply` environment variable:

- `AWS_TERRAFORM_APPLY_ROLE_ARN`

Also expose `AWS_REGION` and `TF_STATE_BUCKET` to `staging-apply`. Require a manual reviewer for `staging-apply` so a reviewed plan cannot be applied without explicit approval.

### Plan

Run **Terraform Staging Plan**. The workflow validates all required execution inputs before authenticating to AWS, initializes the remote state backend, validates Terraform, produces `staging.tfplan`, renders a human-readable plan, and uploads both as the `staging-terraform-plan` artifact.

Record the workflow run ID after reviewing the plan. Do not apply a plan that contains unexpected replacement, deletion, networking, IAM, database, or public-ingress changes.

### Apply

Run **Terraform Staging Apply** with:

- `confirmation`: `APPLY-STAGING`
- `plan_run_id`: the exact reviewed plan workflow run ID

The apply workflow downloads that plan artifact, re-renders the binary plan, verifies it exactly matches the reviewed plan text, and only then runs `terraform apply`. This prevents an operator from silently generating a new plan at apply time.

## Local validation only

For development-time formatting and validation without applying resources:

```bash
cd infra/terraform/aws/staging
terraform fmt -check
terraform init -backend=false
terraform validate
```

Do not use local `terraform apply` for the shared staging environment except during a documented recovery procedure.

## Required GitHub `staging` deployment variables

After Terraform apply, configure the ECS release workflows from Terraform outputs and AWS resource names:

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

The ECS deployment role must trust the repository's protected `staging` environment and should have only the ECR/ECS permissions required to push images, read/register task definitions, update the two staging services, and inspect service state.

## DNS and TLS

Point the staging web and API hostnames to `terraform output -raw alb_dns_name`. Configure an ACM certificate in `STAGING_ACM_CERTIFICATE_ARN` before acceptance testing. When a certificate is configured, port 80 redirects to HTTPS and the HTTPS listener routes configured backend paths to the backend target group; all other traffic goes to the frontend target group.

Do not mark staging accepted until both target groups are healthy and the public endpoints pass HTTPS smoke tests.

## Service bootstrap and normal releases

Terraform creates the ECS services with the immutable bootstrap backend and frontend images. After the services exist, normal releases should use the repository's staging ECS deployment workflows rather than Terraform image changes. Those workflows replace only the container image in the current task definition, wait for service stability, and preserve the existing runtime configuration and secret bindings.

For every release, use one exact 40-character commit SHA contained in protected `main`. Record the ECR digest, resulting task-definition revision, running service state, target health, and smoke-test results in the staging acceptance evidence.

## Database safety

RDS deletion protection is enabled and a final snapshot is required. Terraform destroy will fail until deletion protection is intentionally disabled. This is deliberate to reduce accidental data loss.

## Destroy

Destroying staging is a controlled operation. First back up required data, disable deletion protection in a reviewed change, apply that change, and only then run a separately reviewed destroy procedure. Do not repurpose the normal staging apply workflow for destruction.
