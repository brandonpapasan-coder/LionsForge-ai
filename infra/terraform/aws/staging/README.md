# AWS Staging Infrastructure

This Terraform stack provisions a persistent LionsForge AI staging foundation on AWS:

- VPC with public, private, and database subnets across two availability zones
- Amazon EKS cluster with a managed node group
- Private Amazon RDS for PostgreSQL 16
- Database security rules limited to EKS worker nodes
- Encrypted database storage, backups, deletion protection, and a final snapshot

## Cost warning

Applying this stack creates billable AWS resources, including EKS, EC2, NAT Gateway, RDS, data transfer, and load balancers created later by Kubernetes ingress. Review estimated monthly cost before applying.

## Prerequisites

- Terraform 1.8 or later
- AWS CLI authenticated to the target account
- IAM permission to manage VPC, EKS, EC2, IAM, RDS, and related resources
- A secure remote Terraform state backend before team or production use

## Provision

```bash
cd infra/terraform/aws/staging
terraform init
terraform plan -out staging.tfplan
terraform apply staging.tfplan
```

Use a dedicated AWS account or tightly isolated staging account where possible.

## Configure Kubernetes access

Run the command returned by:

```bash
terraform output -raw configure_kubectl_command
```

Then verify:

```bash
kubectl cluster-info
kubectl get nodes
```

## Configure GitHub staging secrets

Generate the kubeconfig and encode it:

```bash
aws eks update-kubeconfig \
  --region "$(terraform output -raw aws_region)" \
  --name "$(terraform output -raw eks_cluster_name)"

base64 < "$HOME/.kube/config" | tr -d '\n'
```

Store the result as `KUBE_CONFIG_STAGING` in the GitHub `staging` environment.

Retrieve the database connection string without printing it into shared logs:

```bash
terraform output -raw database_url
```

Store it as `STAGING_DATABASE_URL`.

Also configure:

- `STAGING_JWT_SECRET_KEY`
- `STAGING_TEST_EMAIL`
- `STAGING_TEST_SECRET`
- `STAGING_API_URL`
- `STAGING_WEB_URL`

## Ingress, DNS, and TLS

The Kubernetes manifests expect these hostnames:

- `api.staging.lionsforge.ai`
- `staging.lionsforge.ai`

Install an ingress controller and certificate manager after the cluster is available. Create DNS records pointing both hostnames to the ingress load balancer. Do not run acceptance testing until HTTPS is valid for both endpoints.

## Database safety

RDS deletion protection is enabled and a final snapshot is required. Terraform destroy will fail until deletion protection is intentionally disabled. This is deliberate to reduce accidental data loss.

## Destroy

Destroying this environment is a controlled operation. First back up required data, then explicitly disable deletion protection in the stack, apply that change, and only then run:

```bash
terraform destroy
```
