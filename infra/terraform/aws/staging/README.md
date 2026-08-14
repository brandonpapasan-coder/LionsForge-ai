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
- AWS CLI authenticated to the staging AWS account
- IAM permission to manage VPC, ECS, ECR, ELBv2, IAM, CloudWatch Logs, EC2 security groups, and RDS
- a secure remote Terraform state backend
- initial backend and frontend container image URIs that can start successfully
- an ACM certificate ARN when HTTPS is enabled
- backend application secrets stored in AWS Secrets Manager or SSM Parameter Store

Never put secret values in `.tfvars`, source control, workflow output, or issue comments. `backend_secrets` accepts only secret or parameter ARNs; ECS resolves the values at runtime.

## Bootstrap variables

Create a local, untracked variable file such as `staging.auto.tfvars` with non-secret infrastructure values only:

```hcl
bootstrap_backend_image  = "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/onyxmane-staging-backend:BOOTSTRAP_SHA"
bootstrap_frontend_image = "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/onyxmane-staging-frontend:BOOTSTRAP_SHA"
acm_certificate_arn      = "arn:aws:acm:us-east-1:ACCOUNT:certificate/EXAMPLE"

backend_secrets = {
  DATABASE_URL    = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:onyxmane/staging/database-url"
  JWT_SECRET_KEY  = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:onyxmane/staging/jwt-secret"
  OPENAI_API_KEY  = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:onyxmane/staging/openai-api-key"
}
```

The example above contains placeholders only. Do not commit real account identifiers, secret values, or private endpoints.

## Provision

```bash
cd infra/terraform/aws/staging
terraform init -backend-config=backend.hcl
terraform fmt -check
terraform validate
terraform plan -out staging.tfplan
terraform apply staging.tfplan
```

Use a dedicated AWS account or tightly isolated staging account where possible.

## Required GitHub `staging` environment variables

After apply, configure the workflow variables from Terraform outputs and AWS resource names:

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

The ECS deployment workflows use GitHub OIDC. The staging deploy role must trust the repository's protected `staging` environment and should have only the ECR/ECS permissions required to push images, read/register task definitions, update the two staging services, and inspect service state.

## DNS and TLS

Point the staging web and API hostnames to `terraform output -raw alb_dns_name`. Configure an ACM certificate in `acm_certificate_arn` before acceptance testing. When a certificate is configured, port 80 redirects to HTTPS and the HTTPS listener routes configured backend paths to the backend target group; all other traffic goes to the frontend target group.

Do not mark staging accepted until both target groups are healthy and the public endpoints pass HTTPS smoke tests.

## Service bootstrap and normal releases

Terraform creates the ECS services with `bootstrap_backend_image` and `bootstrap_frontend_image`. After the services exist, normal releases should use the repository's staging ECS deployment workflows rather than Terraform image changes. Those workflows replace only the container image in the current task definition, wait for service stability, and preserve the existing runtime configuration and secret bindings.

For every release, use one exact 40-character commit SHA contained in protected `main`. Record the ECR digest, resulting task-definition revision, running service state, target health, and smoke-test results in the staging acceptance evidence.

## Database safety

RDS deletion protection is enabled and a final snapshot is required. Terraform destroy will fail until deletion protection is intentionally disabled. This is deliberate to reduce accidental data loss.

## Destroy

Destroying staging is a controlled operation. First back up required data, disable deletion protection in a reviewed change, apply that change, and only then run:

```bash
terraform destroy
```
